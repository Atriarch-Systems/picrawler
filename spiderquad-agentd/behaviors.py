"""Named expressive behaviors for spiderquad-agentd.

Ported (GPLv3) from the picrawler examples 14_preset_actions.py and
13_emotional_robot.py — pure coordinate-frame sequences fed to
``crawler.do_step``. These are the robot's *body language*: Virali (closed)
triggers them by name over /action; the sequences themselves live here in the
GPL fork (and double as the seed of the declarative routine library).

Each function takes the live Picrawler and an optional speed. EXPRESSIONS maps
the public name -> function. NON_STANDING lists behaviors that end seated/limp
so the daemon can track pose state correctly.
"""

from time import sleep


def _lerp(a, b, t):
    """Linear-interpolate two 4-leg [x,y,z] poses at fraction t."""
    return [[a[i][k] + (b[i][k] - a[i][k]) * t for k in range(3)] for i in range(len(a))]


def _seq(spider, frames, speed, steps=5, dt=0.0):
    """Play keyframes with coordinate interpolation between consecutive frames.

    `steps` sub-frames are inserted per transition -> smoother motion AND smaller
    per-step servo deltas (gentler current draw). `dt` optionally paces each
    sub-frame. steps=1 reproduces the old chunky behavior.
    """
    if not frames:
        return
    spider.do_step(frames[0], speed)
    prev = frames[0]
    for frame in frames[1:]:
        for s in range(1, steps + 1):
            spider.do_step(_lerp(prev, frame, s / steps), speed)
            if dt:
                sleep(dt)
        prev = frame


def wave(spider, speed=58):
    frames = [
        [[45, 45, -50], [45, 0, -50], [45, 0, -50], [45, 45, -50]],
        [[45, 45, -70], [60, 0, 120], [45, 0, -60], [45, 45, -30]],
        [[45, 45, -70], [-20, 60, 120], [45, 0, -60], [45, 45, -30]],
        [[45, 45, -70], [60, 0, 120], [45, 0, -60], [45, 45, -30]],
        [[45, 45, -70], [-20, 60, 120], [45, 0, -60], [45, 45, -30]],
        [[45, 45, -50], [45, 0, -30], [45, 0, -50], [45, 45, -50]],
        [[45, 45, -50], [45, 0, -40], [45, 0, -50], [45, 45, -50]],
        [[45, 45, -50], [45, 0, -50], [45, 0, -50], [45, 45, -50]],
    ]
    _seq(spider, frames, speed)


def shake_hand(spider, speed=52):
    frames = [
        [[45, 45, -50], [45, 0, -50], [45, 0, -50], [45, 45, -50]],
        [[45, 45, -65], [5, 280, 80], [45, 0, -60], [45, 45, -40]],
        [[45, 45, -65], [5, 280, 100], [45, 0, -60], [45, 45, -40]],
        [[45, 45, -65], [5, 280, -10], [45, 0, -60], [45, 45, -40]],
        [[45, 45, -65], [5, 280, 100], [45, 0, -60], [45, 45, -40]],
        [[45, 45, -65], [5, 280, -10], [45, 0, -60], [45, 45, -40]],
        [[45, 45, -65], [5, 280, 100], [45, 0, -60], [45, 45, -40]],
        [[45, 45, -65], [5, 280, -10], [45, 0, -60], [45, 45, -40]],
        [[45, 45, -65], [5, 100, 10], [45, 0, -60], [45, 45, -40]],
        [[45, 45, -65], [5, 100, 10], [45, 0, -60], [45, 45, -40]],
        [[45, 45, -50], [45, 0, -30], [45, 0, -50], [45, 45, -50]],
        [[45, 45, -50], [45, 0, -40], [45, 0, -50], [45, 45, -50]],
        [[45, 45, -50], [45, 0, -50], [45, 0, -50], [45, 45, -50]],
    ]
    _seq(spider, frames, speed)


def excited(spider, speed=30):
    # DETUNED for power: smaller bounce (-44..-60 vs -30..-80), slower, fewer
    # cycles, longer settle -> lower peak servo current (avoids brownout).
    frames = [
        [[45, 45, -50], [45, 0, -50], [45, 0, -50], [45, 45, -50]],
        [[45, 45, -44], [45, 0, -44], [45, 0, -44], [45, 45, -44]],
        [[45, 45, -60], [45, 0, -60], [45, 0, -60], [45, 45, -60]],
        [[45, 45, -44], [45, 0, -44], [45, 0, -44], [45, 45, -44]],
        [[45, 45, -60], [45, 0, -60], [45, 0, -60], [45, 45, -60]],
        [[45, 45, -50], [45, 0, -50], [45, 0, -50], [45, 45, -50]],
    ]
    _seq(spider, frames, speed, steps=4, dt=0.05)


def nod(spider, speed=45):
    spider.do_step([[45, 45, -50], [45, 0, -50], [45, 0, -50], [45, 45, -50]], 60)
    nod_frames = [
        [[45, 45, -80], [45, 0, -50], [45, 0, -20], [45, 45, -30]],
        [[45, 45, -20], [45, 0, -36], [45, 20, -52], [40, 20, -80]],
        [[45, 45, -80], [45, 0, -50], [45, 0, -20], [45, 45, -30]],
        [[45, 45, -20], [45, 0, -36], [45, 20, -52], [40, 20, -80]],
        [[45, 45, -80], [45, 0, -50], [45, 0, -20], [45, 45, -30]],
    ]
    _seq(spider, nod_frames, speed)
    sleep(0.2)
    _seq(spider, [
        [[45, 45, -80], [45, 0, -50], [45, 0, -40], [45, 45, -40]],
        [[45, 45, -60], [45, 0, -50], [45, 0, -40], [45, 45, -40]],
        [[45, 45, -50], [45, 0, -50], [45, 0, -50], [45, 45, -50]],
    ], 50)


def shake_head(spider, speed=58):
    ready = [
        [[45, 45, -50], [45, 0, -50], [45, 20, -50], [45, 45, -50]],
        [[45, 45, -50], [45, 20, -30], [45, 20, -50], [45, 45, -50]],
        [[45, 45, -50], [45, 45, -50], [45, 20, -50], [45, 45, -50]],
    ]
    twist_butt = [
        [[55, 7, -50], [19, 48, -50], [77, 12, -50], [36, 63, -50]],
        [[19, 48, -50], [55, 7, -50], [36, 63, -50], [77, 12, -50]],
        [[51, 15, -50], [27, 43, -50], [72, 22, -50], [45, 56, -50]],
        [[27, 43, -50], [51, 15, -50], [45, 56, -50], [72, 22, -50]],
        [[45, 45, -50], [45, 45, -50], [45, 45, -50], [45, 45, -50]],
    ]
    _seq(spider, ready, 50)
    _seq(spider, twist_butt, speed)
    sleep(0.5)
    _seq(spider, [
        [[45, 45, -50], [45, 20, -30], [45, 0, -50], [45, 45, -50]],
        [[45, 45, -50], [45, 0, -50], [45, 0, -50], [45, 45, -50]],
    ], 52)


def look_left(spider, speed=50):
    _seq(spider, [[[45, 45, -50], [45, 0, -50], [45, 0, -50], [45, 45, -50]]], speed)
    _seq(spider, [
        [[45, 0, -50], [45, 45, -50], [45, 45, -50], [45, 0, -50]],
        [[0, 45, -50], [45, 45, -50], [45, 45, -50], [45, 0, -50]],
        [[0, 45, -50], [45, 45, -35], [45, 45, -50], [45, 0, -50]],
        [[45, 45, -50], [45, 0, -50], [45, 0, -50], [45, 45, -50]],
    ], speed)


def look_right(spider, speed=50):
    _seq(spider, [[[45, 45, -50], [45, 0, -50], [45, 0, -50], [45, 45, -50]]], speed)
    _seq(spider, [
        [[45, 45, -50], [0, 45, -50], [45, 0, -50], [45, 45, -50]],
        [[45, 45, -35], [0, 45, -50], [45, 0, -50], [45, 45, -50]],
        [[45, 0, -50], [45, 45, -50], [45, 45, -50], [45, 0, -50]],
    ], speed)


def look_up(spider, speed=60):
    _seq(spider, [
        [[45, 45, -50], [45, 0, -50], [45, 0, -50], [45, 45, -50]],
        [[45, 45, -76], [45, 0, -76], [45, 0, -38], [45, 45, -30]],
    ], speed)


def look_down(spider, speed=60):
    _seq(spider, [
        [[45, 45, -50], [45, 0, -50], [45, 0, -50], [45, 45, -50]],
        [[45, 45, -28], [45, 0, -40], [45, 0, -68], [45, 45, -76]],
    ], speed)


def play_dead(spider, speed=55):
    _seq(spider, [
        [[45, 45, -50], [45, 0, -50], [45, 0, -50], [45, 45, -50]],
        [[45, 45, -10], [45, 0, -10], [45, 0, -10], [45, 45, -10]],
    ], 60)
    dead = [
        [[45, 45, 100], [45, 45, 100], [45, 45, 100], [45, 45, 100]],
        [[45, 35, 60], [35, 45, 80], [35, 45, 80], [45, 35, 60]],
        [[35, 45, 80], [45, 35, 60], [45, 35, 60], [35, 45, 80]],
        [[45, 35, 60], [35, 45, 80], [35, 45, 80], [45, 35, 60]],
        [[35, 45, 80], [45, 35, 60], [45, 35, 60], [35, 45, 80]],
        [[45, 35, 60], [35, 45, 80], [35, 45, 80], [45, 35, 60]],
        [[45, 45, 100], [45, 45, 100], [45, 45, 100], [45, 45, 100]],
    ]
    _seq(spider, dead, speed)
    _seq(spider, [[[45, 45, -50], [45, 0, -50], [45, 0, -50], [45, 45, -50]]], 60)


def push_up(spider, speed=30):
    # DETUNED for power: gentler ready (slower), 2 reps not 4, longer settle.
    ready = [
        [[45, 45, -50], [45, 0, -50], [45, 0, -50], [45, 45, -50]],
        [[60, 10, -60], [60, 0, -60], [20, 60, 10], [10, 65, -40]],
        [[70, 0, -76], [70, 0, -76], [0, 130, -40], [0, 130, -40]],
    ]
    reps = [
        [[70, 0, -40], [70, 0, -40], [0, 130, -40], [0, 130, -40]],
        [[70, 0, -76], [70, 0, -76], [0, 130, -40], [0, 130, -40]],
        [[70, 0, -40], [70, 0, -40], [0, 130, -40], [0, 130, -40]],
        [[70, 0, -76], [70, 0, -76], [0, 130, -40], [0, 130, -40]],
    ]
    _seq(spider, ready, 45)
    _seq(spider, reps, speed, steps=5, dt=0.05)
    _seq(spider, [[[45, 45, -50], [45, 0, -50], [45, 0, -50], [45, 45, -50]]], 50)


def twist(spider, speed=55):
    new_step = [[50, 50, -80], [50, 50, -80], [50, 50, -80], [50, 50, -80]]
    for i in range(4):
        for inc in range(30, 60, 5):
            rise = [50, 50, (-80 + inc * 0.5)]
            drop = [50, 50, (-80 - inc)]
            new_step[i] = rise
            new_step[(i + 2) % 4] = drop
            new_step[(i + 1) % 4] = rise
            new_step[(i - 1) % 4] = drop
            spider.do_step(new_step, speed)
            sleep(0.02)
    spider.do_step([[45, 45, -50], [45, 0, -50], [45, 0, -50], [45, 45, -50]], speed)


# Public name -> behavior fn
EXPRESSIONS = {
    "wave": wave,
    "shake_hand": shake_hand,
    "excited": excited,
    "nod": nod,
    "shake_head": shake_head,
    "look_left": look_left,
    "look_right": look_right,
    "look_up": look_up,
    "look_down": look_down,
    "play_dead": play_dead,
    "push_up": push_up,
    "twist": twist,
}

# Behaviors that DON'T end in a standing pose (for pose-state tracking).
NON_STANDING = {"play_dead"}
