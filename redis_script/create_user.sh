#!/bin/sh
set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
export SCRIPT_DIR

. "$ROOT_DIR/lib/password.sh"
. "$SCRIPT_DIR/lib/common.sh"

usage() {
  echo "Uso: $0 <projeto>"
  echo ""
  echo "Cria (se não existir) um usuário ACL isolado para o projeto no Redis,"
  echo "restrito às chaves '<projeto>:*'. Se já existir, nenhuma senha nova é gerada."
  exit 1
}

[ $# -eq 1 ] || usage
PROJECT="$1"

if acl_user_exists "$PROJECT"; then
  echo "ℹ️  Usuário Redis '$PROJECT' já existe. Nenhuma senha nova gerada."
  exit 0
fi

REDIS_PASS="$(generate_password 32)"
create_acl_user_if_needed "$PROJECT" "$REDIS_PASS"

echo "✅ Redis pronto para '$PROJECT'"
echo "  user: $PROJECT"
echo "  keys: $PROJECT:*"
echo "  pass: $REDIS_PASS"
