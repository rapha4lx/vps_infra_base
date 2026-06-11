#!/bin/sh
set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECTS_DIR="$SCRIPT_DIR/projects"
export SCRIPT_DIR

. "$SCRIPT_DIR/lib/common.sh"

usage() {
  echo "Uso: $0 [projeto | all | list | status <projeto> | delete [-f|--force] <projeto>]"
  echo ""
  echo "Comandos:"
  echo "  list              Lista projetos disponíveis"
  echo "  <projeto>         Configura usuários, vhosts e permissões de um projeto"
  echo "  all               Configura todos os projetos"
  echo "  status <projeto>  Exibe o estado atual dos recursos do projeto"
  echo "  delete [-f|--force] <projeto>  Remove usuários e vhosts (use -f para pular confirmação)"
  echo ""
  echo "Exemplos:"
  echo "  $0 list"
  echo "  $0 service_flow"
  echo "  $0 all"
  echo "  $0 status service_flow"
  echo "  $0 delete service_flow"
  echo "  $0 delete -f service_flow"
  exit 1
}

list_projects() {
  if [ ! -d "$PROJECTS_DIR" ]; then
    log "Nenhum projeto encontrado em $PROJECTS_DIR"
    exit 0
  fi

  log "Projetos disponíveis:"
  for d in "$PROJECTS_DIR"/*; do
    [ -d "$d" ] || continue
    name=$(basename "$d")
    if [ -f "$d/config.env" ]; then
      log "  - $name"
    else
      warn "  - $name (⚠️  sem config.env)"
    fi
  done
}

run_project() {
  _project="$1"
  _project_dir="$PROJECTS_DIR/$_project"

  if [ ! -d "$_project_dir" ]; then
    error "❌ Projeto '$_project' não encontrado em $_project_dir"
    exit 1
  fi

  if [ ! -f "$_project_dir/config.env" ]; then
    error "❌ Configuração não encontrada: $_project_dir/config.env"
    exit 1
  fi

  while read -r line || [ -n "$line" ]; do
    [ -z "$line" ] || [ "${line#\#}" != "$line" ] && continue
    key="${line%%=*}"
    value="${line#*=}"
    value=$(printf '%s' "$value" | sed -e 's/^"//' -e 's/"$//')
    export "$key=$value"
  done < "$_project_dir/config.env"

  : "${RABBITMQ_USER:?RABBITMQ_USER não definido em config.env}"
  : "${RABBITMQ_PASS:?RABBITMQ_PASS não definido em config.env}"
  : "${RABBITMQ_VHOST:?RABBITMQ_VHOST não definido em config.env}"

  log "🚀 Configurando RabbitMQ para '$_project'..."
  log "   Usuário: $RABBITMQ_USER"
  log "   VHost: $RABBITMQ_VHOST"

  create_user_if_needed "$RABBITMQ_USER" "$RABBITMQ_PASS" "${RABBITMQ_TAGS:-management}"
  create_vhost_if_needed "$RABBITMQ_VHOST"
  set_permissions "$RABBITMQ_USER" "$RABBITMQ_VHOST" \
    "${RABBITMQ_PERM_CONFIGURE:-.*}" \
    "${RABBITMQ_PERM_READ:-.*}" \
    "${RABBITMQ_PERM_WRITE:-.*}"

  success "✅ RabbitMQ configurado para '$_project'!"
}

delete_project() {
  _project="$1"
  _force="${2:-false}"
  _project_dir="$PROJECTS_DIR/$_project"

  if [ ! -f "$_project_dir/config.env" ]; then
    error "❌ Configuração não encontrada: $_project_dir/config.env"
    exit 1
  fi

  while read -r line || [ -n "$line" ]; do
    [ -z "$line" ] || [ "${line#\#}" != "$line" ] && continue
    key="${line%%=*}"
    value="${line#*=}"
    value=$(printf '%s' "$value" | sed -e 's/^"//' -e 's/"$//')
    export "$key=$value"
  done < "$_project_dir/config.env"

  : "${RABBITMQ_USER:?RABBITMQ_USER não definido em config.env}"
  : "${RABBITMQ_VHOST:?RABBITMQ_VHOST não definido em config.env}"

  if [ "$_force" != "true" ]; then
    warn "!!! ATENÇÃO: Isso removerá permanentemente:"
    log "   Usuário: $RABBITMQ_USER"
    log "   VHost:   $RABBITMQ_VHOST"
    log "   (todas as filas, mensagens e bindings serão perdidos)"
    printf "Tem certeza? [y/N] "
    read -r yn
    case "$yn" in
      [yY]) log "Confirmação recebida. Prosseguindo..." ;;
      *) log "Operação cancelada."; exit 0 ;;
    esac
  fi

  log "🗑️  Removendo configuração do RabbitMQ para '$_project'..."
  delete_user_if_exists "$RABBITMQ_USER"
  delete_vhost_if_exists "$RABBITMQ_VHOST"
  success "✅ Configuração removida para '$_project'!"
}

status_project() {
  _project="$1"
  _project_dir="$PROJECTS_DIR/$_project"

  if [ ! -d "$_project_dir" ]; then
    error "❌ Projeto '$_project' não encontrado em $_project_dir"
    exit 1
  fi

  if [ ! -f "$_project_dir/config.env" ]; then
    error "❌ Configuração não encontrada: $_project_dir/config.env"
    exit 1
  fi

  while read -r line || [ -n "$line" ]; do
    [ -z "$line" ] || [ "${line#\#}" != "$line" ] && continue
    key="${line%%=*}"
    value="${line#*=}"
    value=$(printf '%s' "$value" | sed -e 's/^"//' -e 's/"$//')
    export "$key=$value"
  done < "$_project_dir/config.env"

  : "${RABBITMQ_USER:?RABBITMQ_USER não definido em config.env}"
  : "${RABBITMQ_VHOST:?RABBITMQ_VHOST não definido em config.env}"

  _tags="${RABBITMQ_TAGS:-management}"
  _perm_cfg="${RABBITMQ_PERM_CONFIGURE:-.*}"
  _perm_read="${RABBITMQ_PERM_READ:-.*}"
  _perm_write="${RABBITMQ_PERM_WRITE:-.*}"

  log "📊 Status do projeto '$_project':"

  if rabbitmqctl_exec list_users | grep -q "^$RABBITMQ_USER[[:space:]]"; then
    success "  Usuário:  $RABBITMQ_USER ($_tags)        ✅ existe"
  else
    error "  Usuário:  $RABBITMQ_USER ($_tags)        ❌ não existe"
  fi

  if rabbitmqctl_exec list_vhosts | grep -q "^$RABBITMQ_VHOST$"; then
    success "  VHost:    $RABBITMQ_VHOST                  ✅ existe"
  else
    error "  VHost:    $RABBITMQ_VHOST                  ❌ não existe"
  fi

  _vhost_exists=$(rabbitmqctl_exec list_vhosts | grep -c "^$RABBITMQ_VHOST$" || true)
  if [ "$_vhost_exists" -gt 0 ]; then
    _perms=$(rabbitmqctl_exec list_permissions -p "$RABBITMQ_VHOST" | grep -F "$RABBITMQ_USER" || true)
    if [ -n "$_perms" ]; then
      success "  Perm:     configure=$_perm_cfg read=$_perm_read write=$_perm_write  ✅ configuradas"
    else
      warn "  Perm:     configure=$_perm_cfg read=$_perm_read write=$_perm_write  ⚠️ não configuradas"
    fi
  else
    warn "  Perm:     configure=$_perm_cfg read=$_perm_read write=$_perm_write  ⚠️ (vhost não existe)"
  fi
}

if [ $# -eq 0 ]; then
  usage
fi

CMD="$1"

case "$CMD" in
  list)
    list_projects
    ;;
  all)
    for d in "$PROJECTS_DIR"/*; do
      [ -d "$d" ] || continue
      name=$(basename "$d")
      run_project "$name"
    done
    ;;
  delete)
    force=false
    project_name=""
    while [ $# -gt 1 ]; do
      case "$2" in
        -f|--force) force=true; shift ;;
        *) project_name="$2"; shift ;;
      esac
    done
    if [ -z "$project_name" ]; then
      error "❌ Especifique o projeto para deletar."
      usage
    fi
    delete_project "$project_name" "$force"
    ;;
  status)
    if [ -z "${2:-}" ]; then
      error "❌ Especifique o projeto."
      usage
    fi
    status_project "$2"
    ;;
  *)
    run_project "$CMD"
    ;;
esac
