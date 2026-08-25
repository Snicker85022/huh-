#!/usr/bin/env bash
# One-time setup for the sandboxed code-runner user (run as the account that will
# run the scheduler, i.e. taza; needs sudo). Idempotent.
set -euo pipefail

SUSER=${SUSER:-ornith-sandbox}
SBASE=/var/lib/ornith-sandbox
SWORK=$SBASE/workspaces

if ! id -u "$SUSER" >/dev/null 2>&1; then
  sudo useradd --system --no-create-home --shell /usr/sbin/nologin "$SUSER"
  echo "created system user $SUSER"
fi

sudo install -d -o root -g root -m 0755 "$SBASE"
sudo install -d -o root -g "$SUSER" -m 0770 "$SWORK"

sudo usermod -aG "$SUSER" taza || true

# Scoped, auditable sudo rule: taza may run commands AS the sandbox user, no password.
printf 'taza ALL=(%s) NOPASSWD: ALL\n' "$SUSER" | sudo tee /etc/sudoers.d/ornith-sandbox >/dev/null
sudo chmod 0440 /etc/sudoers.d/ornith-sandbox
sudo visudo -c -f /etc/sudoers.d/ornith-sandbox

echo "OK: sandbox user=$SUSER workspace_root=$SWORK (root:$SUSER 0770)"
echo "NOTE: taza was added to group $SUSER; new shells/logins pick it up automatically."
