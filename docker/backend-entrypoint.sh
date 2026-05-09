#!/bin/sh
set -eu

python manage.py migrate --noinput
python manage.py collectstatic --noinput

if [ "${APP_SERVER:-gunicorn}" = "daphne" ]; then
  exec daphne \
    --bind 0.0.0.0 \
    --port 8000 \
    --proxy-headers \
    core.asgi:application
fi

exec gunicorn core.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers "${GUNICORN_WORKERS:-3}" \
  --timeout "${GUNICORN_TIMEOUT:-60}" \
  --access-logfile - \
  --error-logfile -
