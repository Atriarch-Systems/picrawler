#!/usr/bin/env python3
"""spiderquad-agentd -- local control/sense API for atriarch-spider-quad (PiCrawler).

GPLv3 (ships in the picrawler fork). This process imports picrawler / robot_hat /
picamera2 freely. Closed clients (e.g. Virali) talk to it over HTTP and must NOT
import picrawler -- the HTTP boundary keeps them at arm's length (mere aggregation).

Flows:
  sense (from robot):  GET /stats  GET /camera/snapshot  GET /sonar  GET /mic/capture
  act   (to robot):    POST /move  POST /pose  POST /speak  POST /play  POST /volume

Env: SQ_PORT(8970) SQ_MIC(plughw:3,0) SQ_SPK(plughw:CARD=sndrpihifiberry,DEV=0)
Trust model: bind LAN (local/VPN only), no auth -- matches the other surfaces.
"""
import io, os, time, shutil, subprocess, tempfile, threading
from flask import Flask, request, jsonify, Response

import behaviors  # named expressive behaviors (same dir)

MIC = os.environ.get("SQ_MIC", "plughw:3,0")
SPK = os.environ.get("SQ_SPK", "plughw:CARD=sndrpihifiberry,DEV=0")
PORT = int(os.environ.get("SQ_PORT", "8970"))

# Brownout guard: high-current behaviors are refused below this pack voltage.
# (Robot HAT ~5V/3A can't cover big multi-servo surges on a sagging battery.)
SURGE_ACTIONS = {"excited", "push_up", "twist"}
MIN_SURGE_V = float(os.environ.get("SQ_MIN_SURGE_V", "6.9"))
# Disabled outright: dance's surge wedges the HAT MCU/ADC (battery read drops to 0).
DISABLED_ACTIONS = {"dance"}

_lock_motion = threading.Lock()
_lock_cam = threading.Lock()
_lock_audio = threading.Lock()
_crawler = None
_cam = None
_sonar = None
_standing = False

app = Flask(__name__)


def crawler():
    global _crawler
    if _crawler is None:
        from picrawler import Picrawler
        _crawler = Picrawler()
        time.sleep(0.3)
    return _crawler


def camera():
    global _cam
    if _cam is None:
        from picamera2 import Picamera2
        c = Picamera2()
        c.configure(c.create_still_configuration(main={"size": (1280, 720)}))
        c.start()
        time.sleep(0.5)
        _cam = c
    return _cam


def sonar():
    global _sonar
    if _sonar is None:
        from robot_hat import Ultrasonic, Pin
        _sonar = Ultrasonic(Pin("D2"), Pin("D3"))
    return _sonar


def _play(path, volume=None):
    """Blocking playback to the I2S speaker; optional software volume via sox."""
    src = path
    tmp = None
    if volume is not None and shutil.which("sox"):
        tmp = path + ".vol.wav"
        try:
            subprocess.run(["sox", path, tmp, "vol", str(max(0.0, float(volume) / 100.0))],
                           check=True, capture_output=True)
            src = tmp
        except subprocess.CalledProcessError:
            src = path
    with _lock_audio:
        subprocess.run(["aplay", "-q", "-D", SPK, src], check=False)
    if tmp:
        try:
            os.remove(tmp)
        except OSError:
            pass


def _throttled():
    try:
        out = subprocess.check_output(["vcgencmd", "get_throttled"], text=True).strip()
        v = int(out.split("=")[1], 16)
        return {"throttled_raw": hex(v), "undervoltage_now": bool(v & 0x1),
                "throttled_now": bool(v & 0x4), "undervoltage_since_boot": bool(v & 0x10000)}
    except Exception:
        return {}


def _battery():
    try:
        from robot_hat import utils
        v = round(float(utils.get_battery_voltage()), 2)
        pct = max(0, min(100, round((v - 6.2) / (8.4 - 6.2) * 100)))
        return {"battery_v": v, "battery_pct": pct, "low": v < 6.6}
    except Exception:
        return {}


@app.get("/health")
def health():
    return jsonify(ok=True, service="spiderquad-agentd", version=1)


@app.get("/stats")
def stats():
    import psutil
    vm = psutil.virtual_memory()
    try:
        temp = round(int(open("/sys/class/thermal/thermal_zone0/temp").read()) / 1000.0, 1)
    except Exception:
        temp = None
    pi = {"cpu_pct": psutil.cpu_percent(interval=0.2),
          "load": list(os.getloadavg()),
          "mem": {"used_mb": vm.used // 1048576, "available_mb": vm.available // 1048576, "pct": vm.percent},
          "disk_pct": psutil.disk_usage("/").percent, "temp_c": temp,
          "uptime_s": int(time.time() - psutil.boot_time())}
    pi.update(_throttled())
    bot = {"standing": _standing}
    try:
        import picrawler
        from picrawler import Picrawler
        bot["picrawler_version"] = getattr(picrawler, "__version__", "?")
        bot["offset_file"] = Picrawler.OFFSET_FILE
    except Exception:
        pass
    # Per-servo COMMANDED state (3-pin servos have no feedback, so this is the
    # last commanded angle + calibration offset, not a measured value). Only
    # available once the crawler exists (after the first motion) — we never
    # construct it here, since constructing snaps all servos.
    if _crawler is not None:
        try:
            pins = list(getattr(_crawler, "PIN_LIST", []))
            pos = list(getattr(_crawler, "servo_positions", []))
            off = list(getattr(_crawler, "offset", []))
            legs = ["FR", "FL", "RL", "RR"]
            joints = ["knee", "thigh", "hip"]
            bot["servos"] = [
                {"i": i, "leg": legs[i // 3], "joint": joints[i % 3],
                 "header": pins[i] if i < len(pins) else None,
                 "angle": round(float(pos[i]), 1),
                 "offset": round(float(off[i]), 2) if i < len(off) else None}
                for i in range(min(12, len(pos)))
            ]
            bot["coords"] = [[round(float(v), 1) for v in c]
                             for c in getattr(_crawler, "current_coord", [])]
        except Exception:
            pass
    return jsonify(power=_battery(), pi=pi, bot=bot)


@app.get("/camera/snapshot")
def snapshot():
    buf = io.BytesIO()
    with _lock_cam:
        camera().capture_file(buf, format="jpeg")
    buf.seek(0)
    return Response(buf.read(), mimetype="image/jpeg")


@app.get("/sonar")
def sonar_read():
    try:
        d = sonar().read()
    except Exception as e:
        return jsonify(error=str(e)), 500
    return jsonify(distance_cm=(round(d, 1) if d and d > 0 else None))


@app.get("/mic/capture")
def mic_capture():
    sec = max(1, min(30, int(round(float(request.args.get("seconds", 3))))))  # arecord -d wants int
    rate = str(request.args.get("rate", "16000"))
    gain = request.args.get("gain")  # optional sox gain dB to fight the weak mic
    fd, path = tempfile.mkstemp(suffix=".wav"); os.close(fd)
    out = path
    try:
        with _lock_audio:
            r = subprocess.run(["arecord", "-D", MIC, "-f", "S16_LE", "-r", rate, "-c", "1",
                                "-d", str(sec), path], capture_output=True)
        if r.returncode != 0:
            return jsonify(error="arecord failed", detail=r.stderr.decode()[-300:]), 500
        if gain and shutil.which("sox"):
            out = path + ".g.wav"
            subprocess.run(["sox", path, out, "gain", str(gain)], check=False)
        data = open(out, "rb").read()
        return Response(data, mimetype="audio/wav")
    finally:
        for p in {path, out}:
            try:
                os.remove(p)
            except OSError:
                pass


@app.post("/move")
def move():
    global _standing
    j = request.get_json(force=True, silent=True) or {}
    action = j.get("action")
    if not action:
        return jsonify(error="action required (forward/backward/turn left/turn right/...)"), 400
    steps = int(j.get("steps", 1)); speed = int(j.get("speed", 50))
    with _lock_motion:
        c = crawler()
        if j.get("auto_stand"):
            c.do_step("stand", max(30, speed // 2)); time.sleep(0.6); _standing = True
        c.do_action(action, steps, speed); _standing = True
        if j.get("auto_sit"):
            c.do_step("sit", max(30, speed // 2)); time.sleep(0.4); _standing = False
    return jsonify(ok=True, action=action, steps=steps, speed=speed, standing=_standing)


@app.post("/pose")
def pose():
    global _standing
    j = request.get_json(force=True, silent=True) or {}
    # gentler default sweep (lower speed -> more interpolation steps -> lower
    # peak current on the all-legs-together stand/sit "zeroing" move)
    speed = int(j.get("speed", 32))
    with _lock_motion:
        c = crawler()
        if "name" in j:
            c.do_step(j["name"], speed); _standing = (j["name"] == "stand")
        elif "coords" in j:
            c.do_step(j["coords"], speed)
        else:
            return jsonify(error="name or coords required"), 400
    return jsonify(ok=True, standing=_standing)


@app.get("/behaviors")
def behaviors_list():
    """List everything /action accepts, grouped."""
    return jsonify(
        locomotion=["forward", "backward", "turn left", "turn right",
                    "turn left angle", "turn right angle"],
        poses=["stand", "sit"],
        actions=[],
        expressions=sorted(behaviors.EXPRESSIONS.keys()),
    )


@app.post("/action")
def action():
    """Run any named behavior: a gait, a pose, the library 'dance', or an
    expressive sequence (wave/nod/excited/...). See GET /behaviors."""
    global _standing
    j = request.get_json(force=True, silent=True) or {}
    name = (j.get("name") or "").strip()
    if not name:
        return jsonify(error="name required", hint="GET /behaviors"), 400
    if name in DISABLED_ACTIONS:
        return jsonify(error=f"'{name}' is disabled (surge wedges the HAT)", action=name), 409
    speed = j.get("speed")
    steps = int(j.get("steps", 1))
    if name in SURGE_ACTIONS:
        bv = _battery().get("battery_v")
        if bv is not None and bv < MIN_SURGE_V:
            return jsonify(error="battery too low for high-surge action",
                           battery_v=bv, min_surge_v=MIN_SURGE_V, action=name), 409
    with _lock_motion:
        c = crawler()
        if name in behaviors.EXPRESSIONS:
            fn = behaviors.EXPRESSIONS[name]
            if speed:
                fn(c, int(speed))
            else:
                fn(c)
            _standing = name not in behaviors.NON_STANDING
        elif name in ("forward", "backward", "turn left", "turn right",
                      "turn left angle", "turn right angle"):
            c.do_action(name, steps, int(speed) if speed else 50)
            _standing = True
        elif name in ("stand", "sit"):
            c.do_step(name, int(speed) if speed else 45)
            _standing = (name == "stand")
        else:
            return jsonify(error=f"unknown action '{name}'", hint="GET /behaviors"), 400
    return jsonify(ok=True, action=name, standing=_standing)


@app.post("/speak")
def speak():
    j = request.get_json(force=True, silent=True) or {}
    text = (j.get("text") or "").strip()
    if not text:
        return jsonify(error="text required"), 400
    fd, path = tempfile.mkstemp(suffix=".wav"); os.close(fd)
    try:
        if shutil.which("pico2wave"):
            r = subprocess.run(["pico2wave", "-w", path, text], capture_output=True)
        else:
            r = subprocess.run(["espeak", "-w", path, text], capture_output=True)
        if r.returncode != 0:
            return jsonify(error="tts failed", detail=r.stderr.decode()[-300:]), 500
        _play(path, j.get("volume"))
        return jsonify(ok=True, spoke=text)
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


@app.post("/play")
def play():
    vol = request.args.get("volume")
    ctype = (request.content_type or "")
    ext = ".wav" if "wav" in ctype or not request.data else ".audio"
    fd, path = tempfile.mkstemp(suffix=ext); os.close(fd)
    out = path
    try:
        if request.data:
            open(path, "wb").write(request.data)
        else:
            j = request.get_json(force=True, silent=True) or {}
            url = j.get("url")
            if not url:
                return jsonify(error="send audio bytes (audio/wav) or JSON {url}"), 400
            import requests as rq
            open(path, "wb").write(rq.get(url, timeout=15).content)
        if not path.endswith(".wav") and shutil.which("sox"):
            out = path + ".wav"
            subprocess.run(["sox", path, out], check=False)
        _play(out, vol)
        return jsonify(ok=True)
    finally:
        for p in {path, out}:
            try:
                os.remove(p)
            except OSError:
                pass


@app.post("/volume")
def volume():
    j = request.get_json(force=True, silent=True) or {}
    lvl = int(j.get("level", 80))
    try:
        from robot_hat import Music
        Music().music_set_volume(lvl)
    except Exception:
        pass
    return jsonify(ok=True, level=lvl)


def _enable_amp():
    """Power the robot-hat speaker amplifier (pinctrl-held, persists). Without
    this the I2S DAC plays into a disabled amp = silence."""
    try:
        from robot_hat.utils import enable_speaker
        enable_speaker()
        print("speaker amp enabled")
    except Exception as e:
        print("enable_speaker failed:", e)


if __name__ == "__main__":
    print("spiderquad-agentd on :%d  mic=%s spk=%s" % (PORT, MIC, SPK))
    _enable_amp()
    app.run(host="0.0.0.0", port=PORT, threaded=True)
