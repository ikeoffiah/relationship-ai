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

# A Celery worker inside the web container. This is a pilot arrangement and
# would be wrong in production — it cannot scale separately, it dies with the
# web process, and it shares 512 MB with gunicorn.
#
# It is here because the alternative is worse. Partner invites are dispatched
# with send_invite_email.delay(), correctly: sending inline blocked the web
# worker on SMTP and two invites took down the whole API. But .delay() only
# enqueues. With no worker consuming the queue the API returns success, the
# invite row commits, the user is told the invite was sent, and no email is
# ever delivered — and pairing is the one thing a two-person pilot must do.
#
# Render's background workers are paid-only, so on the free tier this is the
# only way to have both a non-blocking API and invites that actually arrive.
# Flags trim the footprint: one process, and none of the peer-discovery
# chatter that matters only with multiple workers.
if [ "${RUN_EMBEDDED_WORKER:-1}" = "1" ]; then
  celery -A config worker \
    --loglevel=info \
    --concurrency=1 \
    --without-gossip --without-mingle --without-heartbeat \
    -Q celery,memory_updates,insight_synthesis,notifications,exports &
  echo "started embedded celery worker (pid $!) — pilot only"
fi

# exec so gunicorn becomes PID 1 and receives SIGTERM directly. Without it the
# shell holds PID 1, swallows the signal, and the platform waits out its grace
# period before killing the container on every single deploy.
exec gunicorn config.wsgi:application \
  --bind "0.0.0.0:${PORT:-8000}" \
  --access-logfile - \
  --error-logfile -
