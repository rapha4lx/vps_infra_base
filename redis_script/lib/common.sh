#!/bin/sh
set -eu

# ============================================
# Biblioteca comum para operações Redis (ACL)
# ============================================

CONTAINER_NAME="${REDIS_CONTAINER:-nginx_redis}"

if [ -z "${SCRIPT_DIR:-}" ]; then
  SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
fi
ENV_FILE="$(cd "$SCRIPT_DIR/.." && pwd)/.env"
REDIS_ADMIN_PASS="${REDIS_PASSWORD:-$(grep '^REDIS_PASSWORD=' "$ENV_FILE" | head -n1 | cut -d'=' -f2- | sed -e 's/^"//' -e 's/"$//')}"

redis_exec() {
  docker exec -i "$CONTAINER_NAME" redis-cli -a "$REDIS_ADMIN_PASS" --no-auth-warning "$@"
}

acl_user_exists() {
  redis_exec ACL LIST | grep -q "^user $1 "
}

create_acl_user_if_needed() {
  _user="$1"
  _pass="$2"

  if acl_user_exists "$_user"; then
    echo "ℹ️  Usuário Redis '$_user' já existe."
  else
    echo "🔑 Criando usuário Redis '$_user'..."
    redis_exec ACL SETUSER "$_user" on ">$_pass" resetchannels "~$_user:*" "+@all" "-@dangerous" "+info"
    redis_exec ACL SAVE
    echo "✅ Usuário Redis '$_user' criado (chaves restritas a '$_user:*')."
  fi
}
