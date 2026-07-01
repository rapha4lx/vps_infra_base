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
  echo "Cria (se não existir) usuário e vhost isolados para o projeto no RabbitMQ."
  echo "Se o usuário já existir, nenhuma senha nova é gerada."
  exit 1
}

[ $# -eq 1 ] || usage
PROJECT="$1"

RABBITMQ_USER="$PROJECT"
RABBITMQ_VHOST="/$PROJECT"

if rabbitmqctl_exec list_users | grep -q "^$RABBITMQ_USER[[:space:]]"; then
  log "ℹ️  Usuário '$RABBITMQ_USER' já existe. Nenhuma senha nova gerada."
  create_vhost_if_needed "$RABBITMQ_VHOST"
  set_permissions "$RABBITMQ_USER" "$RABBITMQ_VHOST" ".*" ".*" ".*"
  exit 0
fi

RABBITMQ_PASS="$(generate_password 32)"

create_user_if_needed "$RABBITMQ_USER" "$RABBITMQ_PASS" "management"
create_vhost_if_needed "$RABBITMQ_VHOST"
set_permissions "$RABBITMQ_USER" "$RABBITMQ_VHOST" ".*" ".*" ".*"

success "✅ RabbitMQ pronto para '$PROJECT'"
echo "  user:  $RABBITMQ_USER"
echo "  vhost: $RABBITMQ_VHOST"
echo "  pass:  $RABBITMQ_PASS"
