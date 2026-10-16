#!/usr/bin/env bash
# arch_collect.sh (v2) -- one box's live facts as TSV. Read-only. No args. Safe anywhere.
# Consumers: arch_scan.py. Never writes, never restarts, never fetches, never installs.
set -u
export LC_ALL=C
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

H=$(hostname)
IP=$(hostname -I 2>/dev/null | awk '{print $1}')
KRN=$(uname -r)
UP=$(uptime -p 2>/dev/null | tr -d '\n')
MEM=$(free -g 2>/dev/null | awk '/^Mem:/{print $2"G total / "$7"G free"}')
DSK=$(df -h / 2>/dev/null | awk 'NR==2{print $2" total / "$4" free"}')
CPU=$(nproc 2>/dev/null)
CPUINFO=$(awk -F': ' '/model name/{print $2; exit}' /proc/cpuinfo 2>/dev/null)
printf 'HOST\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$H" "$IP" "$KRN" "$UP" "$MEM" "$DSK" "$CPU" "$CPUINFO"

# ---- clock facts (D148) -------------------------------------------------
# The INSTANT this box believes, plus where it got it. Epoch only -- never a
# formatted stamp, because gflip is UTC and n100 is America/Phoenix and a
# formatted string is exactly what caused two bugs on 2026-10-16.
CLK_EPOCH=$(date +%s)
CLK_TZ=$(timedatectl show -p Timezone --value 2>/dev/null)
CLK_SRV=$(timedatectl show-timesync -p ServerName --value 2>/dev/null)
CLK_SYNC=$(timedatectl show -p NTPSynchronized --value 2>/dev/null)
CLK_OFF=$(timedatectl timesync-status 2>/dev/null | awk '/Offset:/{print $2}')
CLK_DIST=$(timedatectl timesync-status 2>/dev/null | awk '/Root distance:/{print $3}')
printf 'CLOCK\t%s\t%s\t%s\t%s\t%s\t%s\n' "$CLK_EPOCH" "$CLK_TZ" "$CLK_SRV" "$CLK_SYNC" "$CLK_OFF" "$CLK_DIST"

# ---- every service that is running, and the file that starts it ---------
systemctl list-units --type=service --state=running --no-legend --plain 2>/dev/null | awk '{print $1}' | while read -r u; do
  [ -n "$u" ] || continue
  f=$(systemctl show -p FragmentPath --value "$u" 2>/dev/null)
  a=$(systemctl show -p ExecStart --value "$u" 2>/dev/null | awk -F'argv\\[\\]=' '{print $2}' | cut -d';' -f1)
  w=$(systemctl show -p WorkingDirectory --value "$u" 2>/dev/null)
  printf 'SVC\t%s\t%s\t%s\t%s\n' "$u" "$a" "$f" "$w"
done

# ---- enabled but NOT running / failed (the quiet failures) -------------
systemctl list-unit-files --type=service --state=enabled --no-legend --plain 2>/dev/null | awk '{print $1}' | while read -r u; do
  st=$(systemctl is-active "$u" 2>/dev/null)
  [ "$st" = "active" ] && continue
  f=$(systemctl show -p FragmentPath --value "$u" 2>/dev/null)
  printf 'SVCDEAD\t%s\t%s\t%s\n' "$u" "$st" "$f"
done
systemctl list-units --type=service --state=failed --no-legend --plain 2>/dev/null | awk '{print $1}' | while read -r u; do
  [ -n "$u" ] || continue
  f=$(systemctl show -p FragmentPath --value "$u" 2>/dev/null)
  printf 'SVCDEAD\t%s\tfailed\t%s\n' "$u" "$f"
done

# ---- listening sockets -> process -> owning unit ----------------------
ss -lntup 2>/dev/null | tail -n +2 | while IFS= read -r l; do
  pr=$(echo "$l" | awk '{print $1}')
  ad=$(echo "$l" | awk '{print $5}')
  ow=$(echo "$l" | awk '{print $7}')
  pn=$(echo "$ow" | cut -d'"' -f2)
  pid=$(echo "$ow" | cut -d= -f2 | cut -d, -f1)
  un=
  [ -n "$pid" ] && un=$(grep -o '[^/]*\.service' "/proc/$pid/cgroup" 2>/dev/null | head -1)
  printf 'PORT\t%s\t%s\t%s\t%s\t%s\n' "$pr" "$ad" "$pn" "$pid" "$un"
done

# ---- timers -----------------------------------------------------------
systemctl list-units --type=timer --all --no-legend --plain 2>/dev/null | awk '{print $1}' | while read -r u; do
  [ -n "$u" ] || continue
  nx=$(systemctl show -p NextElapseUSecRealtime --value "$u" 2>/dev/null)
  lt=$(systemctl show -p LastTriggerUSec --value "$u" 2>/dev/null)
  ac=$(systemctl show -p Unit --value "$u" 2>/dev/null)
  printf 'TIMER\t%s\t%s\t%s\t%s\n' "$u" "$nx" "$lt" "$ac"
done

# ---- cron -------------------------------------------------------------
crontab -l 2>/dev/null | grep -v '^#' | grep -v '^[[:space:]]*$' | while read -r l; do printf 'CRON\t%s\n' "$l"; done

# ---- every git checkout on the box ------------------------------------
find /home /opt /srv /mnt -maxdepth 4 -type d -name .git 2>/dev/null | while read -r g; do
  r=${g%/.git}
  b=$(git -C "$r" rev-parse --abbrev-ref HEAD 2>/dev/null)
  h=$(git -C "$r" rev-parse --short HEAD 2>/dev/null)
  d=$(git -C "$r" status --porcelain 2>/dev/null | wc -l)
  bare=$(git -C "$r" rev-parse --is-bare-repository 2>/dev/null)
  up=$(git -C "$r" rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null)
  ah=-; bh=-
  if [ -n "$up" ]; then
    ah=$(git -C "$r" rev-list --count "$up"..HEAD 2>/dev/null)
    bh=$(git -C "$r" rev-list --count HEAD.."$up" 2>/dev/null)
  fi
  rt=$(git -C "$r" rev-list --max-parents=0 HEAD 2>/dev/null | tail -1)
  when=$(git -C "$r" log -1 --format=%cI 2>/dev/null)
  rm=$(git -C "$r" remote -v 2>/dev/null | awk '{print $2}' | sort -u | paste -sd,)
  tr=$(git -C "$r" ls-files 2>/dev/null | wc -l)
  printf 'REPO\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$r" "$b" "$h" "$ah" "$bh" "$d" "$bare" "$rm" "$tr" "$when" "$rt"
done

# ---- one file, how many places? (the shadow-copy detector) ------------
for b in taza-card-table.html board-master.html server_kanban.py ntfy-ack-watcher.py notify.py \
         gig_deck.py checklist_app.py checklist_bootstrap.py sheet_pdf.py service.py \
         printer-selfheal.sh print_when_awake.sh kanban.db world.db deck.json arch_scan.py; do
  find /home /opt -maxdepth 7 -type f -name "$b" -not -path '*/.cache/*' -not -path '*/node_modules/*' \
       -printf 'SHADOW\t%f\t%p\t%s\n' 2>/dev/null
done

# ---- sqlite databases (real ones, not driver caches) ------------------
find /home /opt /srv -maxdepth 5 -type f \( -name '*.db' -o -name '*.sqlite' -o -name '*.sqlite3' \) \
     ! -path '*radv_builtin_shaders*' ! -path '*/.cache/*' ! -path '*.aider.tags.cache*' \
     -printf '%p\t%s\n' 2>/dev/null | while IFS=$'\t' read -r p s; do
  printf 'SQLITE\t%s\t%s\n' "$p" "$s"
done

# ---- postgres ---------------------------------------------------------
if command -v psql >/dev/null 2>&1; then
  psql -Atq -d postgres -c "select version()" 2>/dev/null | while read -r v; do printf 'PGVER\t%s\n' "$v"; done
  # the branch_ids the scan can actually verify its ledger against -- proof, not trust
  psql -Atq -d decisions -c "select string_agg(branch_id,',') from decisions.decisions_log" 2>/dev/null | while read -r v; do [ -n "$v" ] && printf 'LEDGER\t%s\n' "$v"; done
  psql -Atq -d postgres -c "select datname||chr(9)||pg_size_pretty(pg_database_size(datname)) from pg_database where not datistemplate order by datname" 2>/dev/null | while IFS=$'\t' read -r n s; do
    printf 'PGDB\t%s\t%s\n' "$n" "$s"
  done
  cnt() { psql -Atq -d "$1" -c "$2" 2>/dev/null | head -1; }
  while IFS='|' read -r db tbl q; do
    [ -n "$db" ] || continue
    v=$(cnt "$db" "$q")
    [ -n "$v" ] && printf 'PGROW\t%s\t%s\t%s\n' "$db" "$tbl" "$v"
  done <<'SPECS'
decisions|decisions.decisions_log|select count(*) from decisions.decisions_log
decisions|decisions.change_record|select count(*) from decisions.change_record
decisions|decisions.build_log|select count(*) from decisions.build_log
spec|spec.taza_os_user_requirement_specifications|select count(*) from spec.taza_os_user_requirement_specifications
spec|spec.specs|select count(*) from spec.specs
spec|intake.candidate|select count(*) from intake.candidate
tazaos|public.system_events|select count(*) from public.system_events
tazaos|public (table count)|select count(*) from information_schema.tables where table_schema='public'
SPECS
fi

# ---- containers -------------------------------------------------------
if command -v docker >/dev/null 2>&1; then
  docker ps --format '{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}' 2>/dev/null | while IFS=$'\t' read -r n i s p; do
    printf 'DOCKER\t%s\t%s\t%s\t%s\n' "$n" "$i" "$s" "$p"
  done
fi

# ---- the directories that actually matter, by name --------------------
for d in "$HOME" /home/taza/kitchen /home/taza/pm_web /home/taza/scripts /home/taza/repo /home/taza/repo/product/n100 /opt/taza /opt/taza/repo; do
  [ -d "$d" ] || continue
  n=$(find "$d" -maxdepth 1 -mindepth 1 2>/dev/null | wc -l)
  b=$(du -shx "$d" 2>/dev/null | cut -f1)
  ls=$(find "$d" -maxdepth 1 -mindepth 1 -printf '%f ' 2>/dev/null | head -c 1200)
  printf 'LS\t%s\t%s\t%s\t%s\n' "$d" "$n" "$b" "$ls"
done
for f in /home/taza/repo/README-FIRST.md /home/taza/repo/.gitignore /home/taza/pm_web/service.py /home/taza/kitchen/server_kanban.py; do
  [ -f "$f" ] && printf 'FILE\t%s\t%s\t%s\n' "$f" "$(stat -c %s "$f")" "$(stat -c %y "$f" | cut -d. -f1)"
done

# ---- every top-level tree, one line each, so the page can colour each one ----
for base in "$HOME" /opt/taza; do
  [ -d "$base" ] || continue
  for d in "$base"/*/; do
    d="${d%/}"
    [ -d "$d" ] || continue
    [ -L "$d" ] && continue
    n=$(find "$d" -xdev -type f 2>/dev/null | wc -l)
    s=$(du -shx "$d" 2>/dev/null | cut -f1)
    printf 'DIR\t%s\t%s\t%s\n' "$d" "$n" "${s:-?}"
  done
done

# ---- per-user units: invisible to the system units dir, but still services ----
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
if systemctl --user list-unit-files >/dev/null 2>&1; then
  systemctl --user list-unit-files --type=service --no-legend --plain 2>/dev/null | while read -r u state; do
    [ -n "$u" ] || continue
    case "$u" in *.service) ;; *) continue ;; esac
    fp=$(systemctl --user show -p FragmentPath --value "$u" 2>/dev/null)
    case "$fp" in "$HOME"/*) ;; *) continue ;; esac   # ours only; the session's own units are noise
    ar=$(systemctl --user show -p ExecStart --value "$u" 2>/dev/null | cut -c1-300)
    printf 'USVC\t%s (user)\t%s\t%s\t%s\n' "$u" "$ar" "$fp" "$HOME"
  done
fi

# ---- tailscale: is this box on the tailnet, and who else is -----------
if command -v tailscale >/dev/null 2>&1; then
  tailscale status --json 2>/dev/null | python3 -c '
import sys, json
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
s = d.get("Self") or {}
print("TSSTATE\t%s\t%s\t%s" % (d.get("BackendState", "?"), d.get("Version", "?"), s.get("HostName", "")))
def emit(p, kind):
    ips = [i for i in (p.get("TailscaleIPs") or []) if ":" not in i]
    print("TS\t%s\t%s\t%s\t%s\t%s" % (p.get("HostName", "?"), ips[0] if ips else "-", p.get("OS", "?"), "online" if p.get("Online") else "offline", kind))
emit(s, "self")
for p in (d.get("Peer") or {}).values():
    emit(p, "peer")
' 2>/dev/null || true
fi

exit 0
