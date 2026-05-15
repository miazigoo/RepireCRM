#!/bin/sh

set -u

log() {
  printf '%s %s\n' "$(date -Iseconds)" "$*"
}

json_escape() {
  printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'
}

notify() {
  if [ -z "${ALERT_WEBHOOK_URL:-}" ]; then
    return 0
  fi

  text="$(json_escape "$1")"
  curl -fsS -m "${ALERT_WEBHOOK_TIMEOUT_SECONDS:-10}" \
    -H "Content-Type: application/json" \
    -d "{\"text\":\"${text}\"}" \
    "$ALERT_WEBHOOK_URL" >/dev/null 2>&1 || true
}

target_name() {
  printf '%s' "$1" | cut -d= -f1
}

target_url() {
  printf '%s' "$1" | cut -d= -f2-
}

check_url() {
  if [ -n "${MONITOR_HOST_HEADER:-}" ]; then
    curl -fsS -m "$MONITOR_TIMEOUT_SECONDS" -H "Host: ${MONITOR_HOST_HEADER}" "$1" >/dev/null
  else
    curl -fsS -m "$MONITOR_TIMEOUT_SECONDS" "$1" >/dev/null
  fi
}

MONITOR_TARGETS="${MONITOR_TARGETS:-frontend=http://frontend/ backend=http://backend:8000/api/health}"
MONITOR_INTERVAL_SECONDS="${MONITOR_INTERVAL_SECONDS:-60}"
MONITOR_TIMEOUT_SECONDS="${MONITOR_TIMEOUT_SECONDS:-10}"
MONITOR_FAILURE_THRESHOLD="${MONITOR_FAILURE_THRESHOLD:-3}"
MONITOR_HOST_HEADER="${MONITOR_HOST_HEADER:-}"

log "Health monitor started: ${MONITOR_TARGETS}"

while true; do
  for target in $MONITOR_TARGETS; do
    name="$(target_name "$target")"
    url="$(target_url "$target")"
    state_file="/tmp/monitor-${name}.state"
    alert_file="/tmp/monitor-${name}.alerted"
    failures=0

    if [ -f "$state_file" ]; then
      failures="$(cat "$state_file" 2>/dev/null || printf '0')"
    fi

    if check_url "$url"; then
      if [ "$failures" -ge "$MONITOR_FAILURE_THRESHOLD" ] || [ -f "$alert_file" ]; then
        log "Recovered: ${name} ${url}"
        notify "RepairCRM recovered: ${name} ${url}"
      fi
      printf '0' > "$state_file"
      rm -f "$alert_file"
    else
      failures=$((failures + 1))
      printf '%s' "$failures" > "$state_file"
      log "Healthcheck failed (${failures}/${MONITOR_FAILURE_THRESHOLD}): ${name} ${url}"

      if [ "$failures" -ge "$MONITOR_FAILURE_THRESHOLD" ] && [ ! -f "$alert_file" ]; then
        notify "RepairCRM healthcheck FAILED: ${name} ${url}"
        touch "$alert_file"
      fi
    fi
  done

  sleep "$MONITOR_INTERVAL_SECONDS"
done
