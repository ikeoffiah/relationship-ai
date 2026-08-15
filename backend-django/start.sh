#!/usr/bin/env sh
# Start script rather than an inline dockerCommand.
#
# Render passes dockerCommand through in a way that made `sh -c "a && b"` arrive
# as one command name — sh reported the entire string as "not found". Quoting
# rules across YAML, Render and sh are three chances to get it wrong; a file in
# the repo has none.
set -e

# Migrations run here because Render's preDeployCommand is paid-only. This is
# idempotent, so on a wake-from-sleep it costs a second. If it fails the service
# does not start, which is correct: serving an un-migrated database produces
# errors that look like product bugs.
python manage.py migrate --noinput

# exec so gunicorn becomes PID 1 and receives SIGTERM directly. Without it the
# shell holds PID 1, swallows the signal, and the platform waits out its grace
# period before killing the container on every single deploy.
exec gunicorn config.wsgi:application \
  --bind "0.0.0.0:${PORT:-8000}" \
  --access-logfile - \
  --error-logfile -
