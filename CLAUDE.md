# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Picrawler is a Python library for controlling a 4-legged spider robot (SunFounder PiCrawler) on Raspberry Pi. The library handles inverse kinematics, gait generation, and servo control. Version 2.1.4.

## Build / install

Build uses `pyproject.toml` (setuptools, no `setup.py`). Install via pip:

```bash
sudo pip3 install ~/picrawler --break-system-packages
```

For development iteration:

```bash
sudo pip3 uninstall picrawler --break -y && sudo pip3 install . --break --no-deps --no-build-isolation
```

No test suite, linter, or type-checker exists in this repo. Dependencies: `robot_hat` (installed separately from source, 2.5.x branch), `readchar`.

## Architecture

```
picrawler/
  __init__.py          # Exports Picrawler class + __version__
  picrawler.py         # Core library (~650 lines)
  llm.py               # Re-exports LLM classes from robot_hat.llm
  voice_assistant.py   # Re-exports VoiceAssistant from robot_hat.voice_assistant
  stt.py               # Re-exports STT from robot_hat.stt
  tts.py               # Re-exports TTS from robot_hat.tts
  version.py           # Version string (2.1.4)
examples/              # Numbered demo scripts (0-19, matching online course)
  voice_active_crawler.py     # VoiceActiveCrawler class (base, not numbered)
  secret.py                   # API keys (git-ignored)
```

**`picrawler/picrawler.py`** — The single-file core:

- **`Picrawler(Robot)`** — Main class, extends `robot_hat.Robot`. Drives 12 servos (3 per leg × 4 legs) via PWM pins defined in `PIN_LIST`.
  - `coord2polar(coord)` / `polar2coord(angles)` — Inverse and forward kinematics converting between Cartesian leg-tip coordinates (x,y,z) and servo angles (alpha/beta/gamma).
  - `do_step(_step, speed)` — Execute one gait frame: either a list of 4 coordinate-tuples, or a named key into `self.step_list`.
  - `do_action(motion_name, step, speed)` — Repeat a named MoveList action `step` times.
  - `set_angle(angles_list, speed)` — Low-level servo angle write with limit clamping.
  - `cali_helper_web(leg, pos, enter)` — Per-leg calibration adjustment, persists offsets to `~/.config/.picrawler.config`.

- **`Picrawler.MoveList(dict)`** — Inner class defining all gait patterns as `@property` methods. Each property returns a list of frames, where each frame is 4 `[x, y, z]` leg-tip coordinates. Key gaits: `stand`, `sit`, `forward`, `backward`, `turn_left`, `turn_right`, `wave`, `dance`, `push_up`, `look_left/right/up/down`, `turn_left_angle`, `turn_right_angle`. Uses two decorators:
  - `@check_stand` — Auto-prepends `stand` frames if the robot isn't standing.
  - `@normal_action(mode)` — Swaps leg order based on `stand_position` toggle (0 or 1), alternating the supporting vs. lifting legs each cycle.

- Leg ordering in coordinate lists: `[leg0, leg1, leg2, leg3]`.

## Key physical constants

Defined in `MoveList`: `LENGTH_SIDE = 77` (body width), `X_DEFAULT = 45`, `Y_DEFAULT = 45`, `Z_DEFAULT = -50` (standing height), `Z_UP = -30` (sitting/lifted height). All in mm.

## Voice assistant integration (new in 2.5)

`VoiceActiveCrawler` extends `robot_hat.voice_assistant.VoiceAssistant` to provide wake-word-driven AI conversation with action execution. It follows the same pattern as pidog's `VoiceActiveDog`.

### Lifecycle (inherited from VoiceAssistant)

Each conversation round: `before_listen` → wait for wake word → `on_wake` → record speech → `on_heard` → `before_think` → send to LLM → `parse_response` → `before_say` → TTS speaks → `after_say` → `on_finish_a_round`.

`parse_response(text)` splits the LLM response on `ACTIONS: ` delimiter. Left side is the spoken reply, right side is comma-separated action names dispatched to `Picrawler.do_action()`. Actions run on a background thread so they don't block TTS.

### Supported actions

`forward`, `backward`, `turn left`, `turn right`, `sit`, `stand`, `wave`, `push up`, `dance`, `look left`, `look right`, `look up`, `look down` — mapped in `VoiceActiveCrawler.ACTION_MAP`.

### LLM backends

Re-exported from `robot_hat.llm`: `OpenAI`, `Ollama`, `Doubao`, `DeepSeek`, `Gemini`, `Grok`, `Qwen`. Each takes provider-specific kwargs (api_key, model, ip for Ollama, etc.).

## Running examples

Run examples as the **normal user (no `sudo`)** when that user is in the `gpio`, `i2c`, and `spi` groups (the case on this unit); `robot_hat` only needs `sudo` for GPIO/servo access when those groups are missing. Avoid `sudo`: under it `HOME=/root`, which historically split servo calibration between `/root/.config` and the real user's `~/.config`. As of the `atriarch` branch, `Picrawler.OFFSET_FILE` resolves `SUDO_USER`'s home so this can no longer happen -- but running without `sudo` remains the norm. Examples are numbered to match the online course at <https://docs.sunfounder.com/projects/pi-crawler/en/latest/python/play_with_python.html>.

```bash
# Core course examples (0-13)
sudo python3 examples/0_calibration.py       # Servo calibration
sudo python3 examples/1_move.py              # Basic movement
sudo python3 examples/2_keyboard_control.py  # W/A/S/D control
sudo python3 examples/3_sound_effect.py      # Sound effects
sudo python3 examples/4_avoid.py             # Obstacle avoidance
sudo python3 examples/5_display.py           # Camera display
sudo python3 examples/7_bull_fight.py        # Bull fight game
sudo python3 examples/9_preset_actions.py    # Pose demonstration

# Extended examples (14)
sudo python3 examples/14_do_step.py          # Custom step control

# STT/TTS demos (15-16)
sudo python3 examples/15_stt.py              # Speech-to-text
sudo python3 examples/16_tts.py              # Text-to-speech

# Voice AI (17-19)
sudo python3 examples/17_voice_active_crawler_gpt.py     # OpenAI GPT-4o
sudo python3 examples/18_voice_active_crawler_ollama.py   # Local Ollama
sudo python3 examples/19_voice_active_crawler_doubao.py   # Doubao (Chinese)
```

Configure API keys in `examples/secret.py` before running LLM-based examples.

## Calibration data

Servo offset calibration is stored at `~/.config/.picrawler.config`. The file is read/written by `robot_hat.Robot` via the `db` parameter passed to `super().__init__()`.
