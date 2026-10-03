#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"
umask 077

rand() {
  if command -v openssl >/dev/null 2>&1; then openssl rand -hex 32
  else python3 -c 'import secrets; print(secrets.token_hex(32))'
  fi
}

if [ ! -f .env ]; then
  cp .env.example .env
fi

replace_value() {
  key=$1
  value=$2
  tmp=$(mktemp)
  awk -v key="$key" -v value="$value" 'index($0, key "=") == 1 { print key "=" value; next } { print }' .env > "$tmp"
  mv "$tmp" .env
}

# Replace only placeholders, preserving agent credentials provisioned by PhantomLayer.
grep -q '^POSTGRES_PASSWORD=replace-with-' .env && replace_value POSTGRES_PASSWORD "$(rand)"
grep -q '^AUTH_SECRET_KEY=replace-with-' .env && replace_value AUTH_SECRET_KEY "$(rand)"
grep -q '^DEFENDER_EVIDENCE_TOKEN=replace-with-' .env && replace_value DEFENDER_EVIDENCE_TOKEN "$(rand)"

if command -v docker >/dev/null 2>&1; then
  docker network inspect phantomlayer_edge >/dev/null 2>&1 || docker network create phantomlayer_edge >/dev/null
  echo "Ensured Docker network: phantomlayer_edge"
fi

echo "Wrote local runtime configuration to $ROOT/.env"
echo "Next: docker compose up --build -d --wait. Open the bank and follow PhantomLayer customer onboarding."
