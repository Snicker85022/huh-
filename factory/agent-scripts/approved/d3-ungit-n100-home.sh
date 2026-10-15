#!/bin/bash
# D3 (2026-10-15): un-git the n100 home directory.
# /home/taza/.git was an accidental `git init` - unborn master, no commits, no remote.
# Run ON n100 (192.168.2.102) as taza. No sudo needed: taza owns /home/taza/.git.
# Safe: archives .git first, then removes ONLY the .git directory. No files touched.
set -euo pipefail
A=/home/taza/archive/n100-home-dotgit-20261015.tar.gz
tar czf "$A" -C /home/taza .git
echo "members: $(tar tzf "$A" | wc -l)"
sha256sum "$A"
ls -l "$A"
rm -rf /home/taza/.git
if [ -e /home/taza/.git ]; then echo "FAIL: /home/taza/.git still present"; exit 1; fi
echo "PASS: /home/taza/.git removed"
if git -C /home/taza rev-parse --is-inside-work-tree 2>/dev/null; then echo "FAIL: still a repo"; exit 1; else echo "PASS: /home/taza is no longer a git repo"; fi
