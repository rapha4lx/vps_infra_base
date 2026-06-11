#!/bin/sh
set -eu

timestamp() { date '+%Y-%m-%d %H:%M:%S'; }
log()     { echo "$(timestamp) [INFO]  $*"; }
success() { echo "$(timestamp) [OK]    $*"; }
warn()    { echo "$(timestamp) [WARN]  $*" >&3 2>/dev/null || echo "$(timestamp) [WARN]  $*" >&2; }
error()   { echo "$(timestamp) [ERROR] $*" >&2; }

if [ -z "${SCRIPT_DIR:-}" ]; then
  SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
fi
ENV_FILE="$(cd "$SCRIPT_DIR/.." && pwd)/.env"

CONTAINER_NAME="${RABBITMQ_CONTAINER:-nginx_rabbitmq}"
RABBIT_USER="${RABBITMQ_ADMIN_USER:-$(grep '^RABBITMQ_ADMIN_USER=' "$ENV_FILE" | head -n1 | cut -d'=' -f2- | sed -e 's/^"//' -e 's/"$//')}"
RABBIT_PASS="${RABBITMQ_ADMIN_PASS:-$(grep '^RABBITMQ_ADMIN_PASS=' "$ENV_FILE" | head -n1 | cut -d'=' -f2- | sed -e 's/^"//' -e 's/"$//')}"

check_container() {
  if ! docker ps --format '{{.Names}}' 2>/dev/null | grep -qx "$CONTAINER_NAME"; then
    error "Container '$CONTAINER_NAME' não está rodando."
    error "Execute: docker compose up -d rabbitmq"
    exit 1
  fi
}

rabbitmqctl_exec() {
  check_container
  docker exec -i "$CONTAINER_NAME" rabbitmqctl "$@"
}

create_user_if_needed() {
  _user="$1"
  _pass="$2"
  _tags="${3:-administrator}"

  if rabbitmqctl_exec list_users | grep -q "^$_user[[:space:]]"; then
    log "ℹ️  Usuário $_user já existe."
  else
    log "🔑 Criando usuário $_user..."
    rabbitmqctl_exec add_user "$_user" "$_pass"
    rabbitmqctl_exec set_user_tags "$_user" "$_tags"
    success "✅ Usuário $_user criado com tags: $_tags"
  fi
}

create_vhost_if_needed() {
  _vhost="$1"

  if rabbitmqctl_exec list_vhosts | grep -q "^$_vhost$"; then
    log "ℹ️  VHost $_vhost já existe."
  else
    log "📦 Criando vhost $_vhost..."
    rabbitmqctl_exec add_vhost "$_vhost"
    success "✅ VHost $_vhost criado."
  fi
}

set_permissions() {
  _user="$1"
  _vhost="$2"
  _configure="${3:-.*}"
  _read="${4:-.*}"
  _write="${5:-.*}"

  log "🔗 Setando permissões para $_user no vhost $_vhost..."
  rabbitmqctl_exec set_permissions -p "$_vhost" "$_user" "$_configure" "$_read" "$_write"
  success "✅ Permissões configuradas."
}

delete_user_if_exists() {
  _user="$1"
  if rabbitmqctl_exec list_users | grep -q "^$_user[[:space:]]"; then
    log "🗑️  Deletando usuário '$_user'..."
    rabbitmqctl_exec delete_user "$_user"
    success "✅ Usuário '$_user' deletado."
  else
    warn "⚠️  Usuário '$_user' não existe — pulando."
  fi
}

delete_vhost_if_exists() {
  _vhost="$1"
  if rabbitmqctl_exec list_vhosts | grep -q "^$_vhost$"; then
    log "🗑️  Deletando vhost '$_vhost'..."
    rabbitmqctl_exec delete_vhost "$_vhost"
    success "✅ VHost '$_vhost' deletado."
  else
    warn "⚠️  VHost '$_vhost' não existe — pulando."
  fi
}
