# Provisioning — atriarch-spider-quad

Rebuild the whole robot stack on a fresh Raspberry Pi (e.g. after swapping a
brown-out-prone **Pi 5** for a **Pi 4**, which matches the Robot HAT's 5V/3A budget).

## Power reality (why Pi 4)

The SunFounder Robot HAT supplies ~**5V/3A**. A **Pi 5** can pull up to **5V/5A**
and browns out under multi-servo current surges (red LED, spontaneous reboot —
*not* thermal, *not* fixable by downclocking). Use a **Pi 4**, or give the Pi its
own 5V/5A supply with the servos on a separate battery/BEC. Charge the 18650s
fully (they ship at 25–50%); a pack that sags from ~8.3V to ~7V under load is bad.

## One-shot setup

On the fresh Pi, as the **normal user** (e.g. `dp_admin`), with networking up:

```bash
git clone -b atriarch https://github.com/Atriarch-Systems/picrawler.git ~/picrawler
bash ~/picrawler/provision/setup.sh
# log out/in (or reboot) so the new gpio/i2c/spi group membership takes effect
```

`setup.sh` installs deps, joins the hardware groups, installs robot-hat (v2.0) +
vilib + picrawler(@atriarch), runs `i2samp.sh` (speaker), restores the servo
calibration, and installs+enables the **spiderquad-agentd** systemd service.
Verify: `curl -s localhost:8970/health && curl -s localhost:8970/behaviors`.

## Two manual steps (need a password once)

**1. Passwordless SSH** — from your workstation:
```powershell
type $env:USERPROFILE\.ssh\id_rsa_rke2_cluster.pub | ssh dp_admin@<ip> "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
```

**2. Passwordless sudo** — on the Pi (gives a TTY for the one password prompt):
```bash
echo "$USER ALL=(ALL) NOPASSWD:ALL" | sudo tee /etc/sudoers.d/$USER >/dev/null && sudo chmod 440 /etc/sudoers.d/$USER && sudo visudo -c
```

## Enable on the Virali side

Set `SPIDER_QUAD_URL=http://spider-quad.atriarch.internal:8970` in Virali's env
and restart core. (DNS record lives in Atriarch.Engineering
`infrastructure/pihole/local-dns-hosts.txt` → static IP.)

## Critical gotchas

- **Never run picrawler with `sudo`** — `sudo` sets `HOME=/root`, which splits the
  offset config between `/root/.config` and `~/.config`. Membership in
  `gpio/i2c/spi` makes sudo unnecessary. (The atriarch branch also makes
  `OFFSET_FILE` resolve `SUDO_USER` as a backstop.)
- **Speaker** is the I2S DAC (`plughw:CARD=sndrpihifiberry`); the amp must be
  enabled (`robot_hat.enable_speaker()` / pinctrl) or playback is silent — the
  daemon does this at startup.
- Leg servo header order per leg is **[knee, thigh-lift, hip-rotate]**; a swapped
  pair looks fine at zero but wrong in motion.
