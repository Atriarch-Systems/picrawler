#!/usr/bin/env bash
# =============================================================================
# atriarch-spider-quad — one-shot re-provisioner
# Rebuilds the entire robot stack on a fresh Raspberry Pi.
#
#   RUN AS THE NORMAL USER (not root):   bash provision/setup.sh
#
# HARDWARE NOTE: the SunFounder Robot HAT delivers ~5V/3A. A Raspberry Pi 5 can
# draw up to 5V/5A and will BROWN OUT under multi-servo current surges (red LED
# / spontaneous reboot). **Pi 4 is recommended** for this kit — it matches the
# HAT's power budget. Servo calibration offsets are per-robot-BODY and carry
# across Pi swaps (restored below), so a Pi4<->Pi5 swap keeps the same trim.
#
# This does NOT set up SSH key auth or passwordless sudo (those need a password
# once) — see provision/README.md for those two manual steps.
# =============================================================================
set -euo pipefail

U="$(whoami)"; H="$HOME"
REPO="${REPO:-https://github.com/Atriarch-Systems/picrawler.git}"
BRANCH="${BRANCH:-atriarch}"
log() { echo -e "\n\033[1;36m== $* ==\033[0m"; }

if [ "$U" = "root" ]; then echo "Run as the normal user, not root."; exit 1; fi

log "1/9 apt packages"
sudo apt-get update
sudo apt-get install -y git python3-pip python3-setuptools python3-smbus i2c-tools \
  sox libttspico-utils espeak alsa-utils \
  python3-flask python3-requests python3-psutil python3-picamera2

log "2/9 user groups (servo/i2c/audio access WITHOUT sudo — important: sudo's HOME=/root splits the offset config)"
sudo usermod -aG gpio,i2c,spi,audio,video "$U" || true

log "3/9 clone fork + checkout $BRANCH"
cd "$H"
[ -d picrawler/.git ] || git clone "$REPO" picrawler
git -C picrawler remote set-url origin "$REPO"
git -C picrawler remote get-url upstream >/dev/null 2>&1 || \
  git -C picrawler remote add upstream https://github.com/sunfounder/picrawler.git
git -C picrawler fetch origin --quiet
git -C picrawler checkout "$BRANCH"
git -C picrawler pull --ff-only origin "$BRANCH" || true

log "4/9 robot-hat (sunfounder v2.0)"
[ -d "$H/robot-hat" ] || git clone -b v2.0 https://github.com/sunfounder/robot-hat.git "$H/robot-hat"
( cd "$H/robot-hat" && (sudo python3 install.py || sudo pip3 install . --break-system-packages --no-build-isolation) )

log "5/9 vilib (sunfounder main)"
[ -d "$H/vilib" ] || git clone https://github.com/sunfounder/vilib.git "$H/vilib"
( cd "$H/vilib" && (sudo python3 install.py || sudo pip3 install . --break-system-packages --no-build-isolation) )

log "6/9 picrawler (from fork, $BRANCH)"
( cd "$H/picrawler" && sudo pip3 install . --break-system-packages --no-deps --no-build-isolation --force-reinstall )

log "7/9 speaker amp (I2S) — may prompt + reboot; re-run setup after if it reboots"
( cd "$H/robot-hat" && sudo bash i2samp.sh ) || \
  echo "  (skipped) run 'sudo bash ~/robot-hat/i2samp.sh' manually if needed"

log "8/9 restore servo calibration (per-robot-body)"
mkdir -p "$H/.config"
CAL="$H/.config/.picrawler.config"
if [ -f "$H/picrawler/provision/calibration.config" ]; then
  cp "$H/picrawler/provision/calibration.config" "$CAL"
  echo "  restored from provision/calibration.config"
elif [ ! -f "$CAL" ]; then
  cp "$H/picrawler/provision/calibration.config" "$CAL" 2>/dev/null || true
fi
echo "  -> $CAL"; cat "$CAL" 2>/dev/null || echo "  (none — run: cd ~/picrawler && python3 examples/0_calibration.py  [NO sudo])"

log "9/9 spiderquad-agentd systemd service"
sudo tee /etc/systemd/system/spiderquad-agentd.service >/dev/null <<EOF
[Unit]
Description=spiderquad-agentd (PiCrawler control/sense API for Virali)
After=network-online.target sound.target
Wants=network-online.target

[Service]
Type=simple
User=$U
Group=$U
SupplementaryGroups=gpio i2c spi audio video
WorkingDirectory=$H/picrawler/spiderquad-agentd
Environment=SQ_PORT=8970
ExecStart=/usr/bin/python3 $H/picrawler/spiderquad-agentd/agentd.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable --now spiderquad-agentd

log "NTP -> ntp.atriarch.internal (home time server)"
sudo tee /etc/systemd/timesyncd.conf >/dev/null <<EOF
[Time]
NTP=ntp.atriarch.internal
FallbackNTP=192.168.0.4 0.debian.pool.ntp.org
EOF
sudo systemctl restart systemd-timesyncd || true

echo -e "\n\033[1;32mDone.\033[0m"
echo "Verify:   curl -s localhost:8970/health   &&   curl -s localhost:8970/behaviors"
echo "If groups were just added, LOG OUT/IN (or reboot) so non-sudo servo access works."
echo "Then point Virali at it:  SPIDER_QUAD_URL=http://spider-quad.atriarch.internal:8970"
