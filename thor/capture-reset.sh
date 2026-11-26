#!/bin/sh
# Capture the Thor's kernel and journal over SSH, to catch a silent reset.
#
#   thor/capture-reset.sh [DIR]   stream until the device goes away (Ctrl-C to stop)
#   thor/capture-reset.sh reason  print why the device last reset (bootloader log)
#
# Run from the repository root. Reads THOR_HOST, THOR_USER and THOR_SSH_KEY from
# .env. Captures go to DIR (default .build/reset-capture/<time>), which Git ignores.
# Streaming turns on drm.debug=0x100 (DisplayPort messages); a reboot clears it.
set -eu

[ -f .env ] && { set -a; . ./.env; set +a; }
: "${THOR_HOST:?set THOR_HOST in .env}" "${THOR_USER:?set THOR_USER in .env}"
key=${THOR_SSH_KEY:-}
case $key in "~/"*) key=$HOME/${key#\~/} ;; esac

thor() {
	ssh -o ConnectTimeout=8 -o ServerAliveInterval=1 -o ServerAliveCountMax=3 \
		${key:+-i "$key"} "$THOR_USER@$THOR_HOST" "$@"
}

# The bootloader (XBL) keeps its log in reserved memory at 0x81a00000
# (xbl-dt-log-merged-region). Its "PM: Reset by ..." lines name the cause:
# PSHOLD is a reset the SoC asked for (Linux, TrustZone or the hypervisor);
# a PMIC fault would read UVLO, KPDPWR (long power-key press) and so on.
if [ "${1:-}" = reason ]; then
	thor 'sudo python3 -c "
import mmap, os, re
fd = os.open(\"/dev/mem\", os.O_RDONLY | os.O_SYNC)
m = mmap.mmap(fd, 0x26000, mmap.MAP_SHARED, mmap.PROT_READ, offset=0x81a00000)
text = bytes(m[:]).decode(\"ascii\", \"replace\")
for line in text.splitlines():
    if re.match(r\"[BD] - +[0-9]+ - (PM: (Reset|PON|POFF|Fault|VBAT)|ddr_init =)\", line):
        print(line.strip())
"; journalctl --list-boots | tail -4'
	exit
fi

dir=${1:-.build/reset-capture/$(date +%Y%m%d-%H%M%S)}
mkdir -p "$dir"
echo "capturing into $dir"
thor 'echo 0x100 | sudo tee /sys/module/drm/parameters/debug >/dev/null'

thor 'sudo dmesg -w --time-format iso' >"$dir/dmesg.txt" 2>&1 &
k=$!
thor 'journalctl -f -n 0 -o short-iso-precise' >"$dir/journal.txt" 2>&1 &
j=$!
# One line a second: the last one before a gap dates the reset.
thor 'while :; do date +%T.%N; cat /sys/class/drm/card1-DP-1/status; sleep 1; done' \
	>"$dir/heartbeat.txt" 2>&1 &
h=$!
trap 'kill $k $j $h 2>/dev/null' INT TERM
wait $h || true
kill $k $j 2>/dev/null || true
echo "device stopped answering at $(tail -n 2 "$dir/heartbeat.txt" | head -n 1)"
