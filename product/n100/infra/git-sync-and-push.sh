#!/bin/bash
set -euo pipefail
source /home/taza/.env

# Mirror GitHub (huh-) into the USB bare repo. This pulls the mURS
# (canonical repo is now on gflip: ~/repo) plus any legacy branches.
#
# The old /opt/taza/repo force-push to GitHub was REMOVED 2026-09-30:
# it was force-pushing an abandoned HPWT-era repo over the mURS every
# night. Canonical mURS now pushes itself to GitHub from gflip via its
# own nightly timer; this box only mirrors GitHub -> USB.
git -C /mnt/taza-git/git/tazaos.git fetch --all --prune
