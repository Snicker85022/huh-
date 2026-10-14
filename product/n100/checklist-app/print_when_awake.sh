#!/bin/bash
# The HP DeskJet 3700 (192.168.2.118) dropped off the LAN while the checklists were being sent
# (2026-10-08 16:39 MST). This waits for it to come back, then prints the pending PDFs.
Q=HP_DeskJet_3700_series_760AB1
IP=192.168.2.118
LOG=/home/taza/checklist-app/print_when_awake.log
echo "$(date '+%F %T') watcher started - waiting for $IP:631" >> "$LOG"
for i in $(seq 1 120); do          # 120 x 30s = 60 min
  if timeout 2 bash -c "echo > /dev/tcp/$IP/631" 2>/dev/null; then
    echo "$(date '+%F %T') printer is up - sending $(ls /home/taza/checklist-app/out/*.pdf | wc -l) checklist(s)" >> "$LOG"
    for p in /home/taza/checklist-app/out/*.pdf; do
      lp -d "$Q" -o media=na_letter_8.5x11in -o print-color-mode=monochrome \
         -t "CHECKLIST $(basename "$p" .pdf)" "$p" >> "$LOG" 2>&1
    done
    echo "$(date '+%F %T') done" >> "$LOG"
    exit 0
  fi
  sleep 30
done
echo "$(date '+%F %T') gave up after 60 min - printer still offline" >> "$LOG"
