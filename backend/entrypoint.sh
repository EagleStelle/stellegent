#!/bin/sh
# Container entrypoint.
#
# Goal: run the app as the unprivileged `app` user whenever possible, but stay
# functional on hosts (notably Synology NAS) whose bind-mounted shared folders
# reject chown even from container root and are owned by a uid that does not
# match `app`.
#
# Strategy:
#   1. Ensure the data dir exists.
#   2. Best-effort chown it to `app` (silently ignored where not permitted,
#      e.g. Synology shared folders enforcing their own ACL model).
#   3. Test whether `app` can actually write there.
#        - yes -> drop privileges to `app` (least privilege, preferred).
#        - no  -> fall back to running as root, which can still read/write a
#                 foreign-owned dir via CAP_DAC_OVERRIDE even when it cannot
#                 chown it. This is what fixes the Synology
#                 "unable to open database file" error automatically.
set -e

DATA_DIR="${STELLEGENT_DATA:-/app/data}"
case "$DATA_DIR" in
    /*) ;;
    *) DATA_DIR="/app/$DATA_DIR" ;;
esac

mkdir -p "$DATA_DIR" 2>/dev/null || true
chown -R app:app "$DATA_DIR" 2>/dev/null || true

if gosu app sh -c "touch \"$DATA_DIR/.write-test\" 2>/dev/null && rm -f \"$DATA_DIR/.write-test\""; then
    exec gosu app "$@"
fi

echo "entrypoint: '$DATA_DIR' not writable by app user (uid 10001); running as root to honor the bind mount" >&2
exec "$@"
