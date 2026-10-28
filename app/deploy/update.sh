#!/usr/bin/env bash
# Update the hub from GitHub: pull the newest main, run the tests, restart.
# If the tests fail, the clone goes back to the previous commit and the hub
# keeps running the old code; that commit is not retried until main moves on.
#
# Run by hub-update.timer (systemd user unit) or by hand:
#   app/deploy/update.sh            # check and update
#   app/deploy/update.sh --force    # retry a commit that failed before
#
# Environment (all optional):
#   HUB_WORKDIR       hub work folder, status goes to $HUB_WORKDIR/update-status.json
#   HUB_RESTART_CMD   how to restart the hub (default: systemctl --user restart hub.service)
#   HUB_BRANCH        branch to follow (default: main)
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
APP="$REPO/app"
# the same work folder as the hub: env, then config/hub.json, then the default
WORKDIR="${HUB_WORKDIR:-$(python3 -c "import json,os,sys; print(os.path.expanduser(json.load(open(sys.argv[1])).get('workdir','~/hub-work')))" "$APP/config/hub.json" 2>/dev/null || echo "$HOME/hub-work")}"
BRANCH="${HUB_BRANCH:-main}"
RESTART_CMD="${HUB_RESTART_CMD:-systemctl --user restart hub.service}"
STATUS="$WORKDIR/update-status.json"
FORCE="${1:-}"

mkdir -p "$WORKDIR"
exec 9>"$WORKDIR/.update.lock"
flock -n 9 || { echo "update already running"; exit 0; }

log() { echo "$(date '+%F %T') $*"; }

# status file: JSON written by python so messages are always escaped correctly
write_status() {  # result from to message [failed_commit]
  python3 - "$STATUS" "$@" <<'PY'
import json, sys, time
path, result, old, new, message = sys.argv[1:6]
failed = sys.argv[6] if len(sys.argv) > 6 else ""
try:
    with open(path, encoding="utf-8") as f:
        prev = json.load(f)
except (OSError, ValueError):
    prev = {}
data = {"time": time.time(), "result": result, "from": old, "to": new, "message": message,
        "failed_commit": failed or (prev.get("failed_commit", "") if result != "updated" else "")}
tmp = path + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=1)
import os
os.replace(tmp, path)
PY
}

cd "$REPO"
OLD="$(git rev-parse HEAD)"

# the server never edits tracked files: local settings live in gitignored files
if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
  write_status "local-changes" "$OLD" "$OLD" "в клоне правлены файлы из git — обновление остановлено: $(git status --porcelain --untracked-files=no | head -5 | tr '\n' ' ')"
  log "local changes in tracked files, aborting"; exit 1
fi

if ! git fetch --quiet origin "$BRANCH"; then
  write_status "error" "$OLD" "$OLD" "git fetch не удался (нет сети или GitHub недоступен)"
  log "fetch failed"; exit 1
fi
NEW="$(git rev-parse FETCH_HEAD)"

if [ "$NEW" = "$OLD" ]; then
  write_status "up-to-date" "$OLD" "$OLD" "обновлений нет"
  log "up to date at ${OLD:0:7}"; exit 0
fi

PREV_FAILED="$(python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get('failed_commit',''))" "$STATUS" 2>/dev/null || true)"
if [ "$NEW" = "$PREV_FAILED" ] && [ "$FORCE" != "--force" ]; then
  log "${NEW:0:7} failed tests before, waiting for a newer commit (use --force to retry)"; exit 0
fi

if ! git merge-base --is-ancestor "$OLD" "$NEW"; then
  write_status "error" "$OLD" "$NEW" "история $BRANCH переписана — нужен ручной разбор, обновление остановлено"
  log "not a fast-forward, aborting"; exit 1
fi

log "updating ${OLD:0:7} -> ${NEW:0:7}"
git merge --quiet --ff-only "$NEW"

# the browser audit (test_ui_browser) is for development machines; the static UI checks still run here
if (cd "$APP" && HUB_SKIP_BROWSER=1 timeout 900 python3 -m unittest discover -s tests >"$WORKDIR/update-tests.log" 2>&1); then
  CHANGES="$(git log --format='%s' "$OLD..$NEW" | head -10 | tr '\n' ';' | sed 's/;$//')"
  write_status "updated" "$OLD" "$NEW" "$CHANGES"
  log "tests passed, restarting: $RESTART_CMD"
  # the status file is written first: a restart may stop this script when run from the hub
  bash -c "$RESTART_CMD" || { write_status "error" "$OLD" "$NEW" "код обновлён, но перезапуск не удался: $RESTART_CMD"; exit 1; }
else
  git reset --quiet --hard "$OLD"
  write_status "tests-failed" "$OLD" "$NEW" "тесты не прошли на ${NEW:0:7}, остаётся ${OLD:0:7}; лог: $WORKDIR/update-tests.log" "$NEW"
  log "tests failed, rolled back to ${OLD:0:7}"; exit 1
fi
