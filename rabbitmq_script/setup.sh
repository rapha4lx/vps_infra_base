#!/bin/sh
set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECTS_DIR="$SCRIPT_DIR/projects"
export SCRIPT_DIR

. "$SCRIPT_DIR/lib/common.sh"

usage() {
  echo "Uso: $0 [projeto | all | list | delete <projeto>]"
  echo ""
  echo "Comandos:"
  echo "  list              Lista projetos disponíveis"
  echo "  <projeto>         Configura usuários, vhosts e permissões de um projeto"
  echo "  all               Configura todos os projetos"
  echo "  delete <projeto>  Remove usuários e vhosts do projeto (cuidado!)"
  echo ""
  echo "Exemplos:"
  echo "  $0 list"
  echo "  $0 service_flow"
  echo "  $0 all"
  echo "  $0 delete service_flow"
  exit 1
}

list_projects() {
  if [ ! -d "$PROJECTS_DIR" ]; then
    echo "Nenhum projeto encontrado em $PROJECTS_DIR"
    exit 0
  fi

  echo "Projetos disponíveis:"
  for d in "$PROJECTS_DIR"/*; do
    [ -d "$d" ] || continue
    name=$(basename "$d")
    if [ -f "$d/config.env" ]; then
      echo "  - $name"
    else
      echo "  - $name (⚠️  sem config.env)"
    fi
  done
}

run_project() {
  _project="$1"
  _project_dir="$PROJECTS_DIR/$_project"

  if [ ! -d "$_project_dir" ]; then
    echo "❌ Projeto '$_project' não encontrado em $_project_dir"
    exit 1
  fi

  if [ ! -f "$_project_dir/config.env" ]; then
    echo "❌ Configuração não encontrada: $_project_dir/config.env"
    exit 1
  fi

  while IFS='=' read -r key value; do
    case "$key" in
      \#*|""|*\#*) continue ;;
    esac
    value=$(printf '%s' "$value" | sed -e 's/^"//' -e 's/"$//')
    export "$key=$value"
  done < "$_project_dir/config.env"

  : "${RABBITMQ_USER:?RABBITMQ_USER não definido em config.env}"
  : "${RABBITMQ_PASS:?RABBITMQ_PASS não definido em config.env}"
  : "${RABBITMQ_VHOST:?RABBITMQ_VHOST não definido em config.env}"

  echo "🚀 Configurando RabbitMQ para '$_project'..."
  echo "   Usuário: $RABBITMQ_USER"
  echo "   VHost: $RABBITMQ_VHOST"

  create_user_if_needed "$RABBITMQ_USER" "$RABBITMQ_PASS" "${RABBITMQ_TAGS:-management}"
  create_vhost_if_needed "$RABBITMQ_VHOST"
  set_permissions "$RABBITMQ_USER" "$RABBITMQ_VHOST" \
    "${RABBITMQ_PERM_CONFIGURE:-.*}" \
    "${RABBITMQ_PERM_READ:-.*}" \
    "${RABBITMQ_PERM_WRITE:-.*}"

  echo "✅ RabbitMQ configurado para '$_project'!"
}

delete_project() {
  _project="$1"
  _project_dir="$PROJECTS_DIR/$_project"

  if [ ! -f "$_project_dir/config.env" ]; then
    echo "❌ Configuração não encontrada: $_project_dir/config.env"
    exit 1
  fi

  while IFS='=' read -r key value; do
    case "$key" in
      \#*|""|*\#*) continue ;;
    esac
    value=$(printf '%s' "$value" | sed -e 's/^"//' -e 's/"$//')
    export "$key=$value"
  done < "$_project_dir/config.env"

  : "${RABBITMQ_USER:?RABBITMQ_USER não definido em config.env}"
  : "${RABBITMQ_VHOST:?RABBITMQ_VHOST não definido em config.env}"

  echo "🗑️  Removendo configuração do RabbitMQ para '$_project'..."
  delete_user_if_exists "$RABBITMQ_USER"
  delete_vhost_if_exists "$RABBITMQ_VHOST"
  echo "✅ Configuração removida para '$_project'!"
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
    if [ -z "${2:-}" ]; then
      echo "❌ Especifique o projeto para deletar."
      usage
    fi
    delete_project "$2"
    ;;
  *)
    run_project "$CMD"
    ;;
esac
