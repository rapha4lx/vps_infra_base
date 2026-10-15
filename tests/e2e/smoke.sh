#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
docker compose up -d
trap 'docker compose logs --no-color; docker compose down -v --remove-orphans' EXIT
for i in $(seq 1 45); do
  response="$(curl -ksS --connect-timeout 2 --max-time 3 -o /dev/null -w '%{http_code}' -H 'Host: app.test' https://127.0.0.1:18443/ || true)"
  if [[ "$response" == "200" ]]; then break; fi
  sleep 2
done
[[ "$response" == "200" ]] || { echo "Traefik did not reach backend: $response" >&2; exit 1; }
code="$(curl -ksS -o /dev/null -w '%{http_code}' -H 'Host: unlisted.test' https://127.0.0.1:18443/)"
[[ "$code" == "404" ]] || { echo "Unknown hostname was not rejected: $code" >&2; exit 1; }
echo "PASS: HTTPS via Traefik reaches internal backend; unknown hostname rejected"
