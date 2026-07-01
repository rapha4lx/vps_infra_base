#!/bin/sh
set -eu

# Gera senha aleatória contendo letras minúsculas, maiúsculas e caracteres
# especiais. Uso: generate_password [tamanho=32]
generate_password() {
  _length="${1:-32}"
  _charset='A-Za-z0-9!@#%^&*()_+=-'

  while :; do
    _pass=$(LC_ALL=C tr -dc "$_charset" </dev/urandom | head -c "$_length")
    printf '%s' "$_pass" | grep -q '[a-z]' || continue
    printf '%s' "$_pass" | grep -q '[A-Z]' || continue
    printf '%s' "$_pass" | grep -q '[!@#%^&*()_+=-]' || continue
    printf '%s' "$_pass"
    return 0
  done
}
