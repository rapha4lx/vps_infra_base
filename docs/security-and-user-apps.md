# Administração de segurança e aplicativos por usuário

## Atualizar o painel após git pull
```bash
sudo bash setup.sh
sudo systemctl status vps-panel --no-pager
```
A instalação copia o módulo de inventário `session_inventory.py`. No painel,
a aba Segurança mostra sessões logind (inclusive root) e processos SSH associados
quando identificáveis. `who` pode não registrar túneis SSH sem PTY;
`loginctl` também não é exaustivo para todas as conexões. Não usar essa
visão como base exclusiva para encerrar sessões ou investigar incidentes.

## Instalar ferramentas de segurança globais
O painel exibe instruções e estado dos serviços. A execução via interface
ainda não existe para evitar instalação de pacotes privilegiados por um
processo web executando como root.

Em uma sessão de administrador na VPS, após revisar os scripts:
```bash
sudo bash security/install-base.sh
sudo fail2ban-client status sshd
sudo ufw status verbose
sudo sshd -T | grep -E '^(permitrootlogin|passwordauthentication)'
```
`install-base.sh` instala pacotes e configura o jail SSH de Fail2ban,
mas **não** ativa UFW, não muda sudoers e não desabilita SSH root. Essas
mudanças dependem de console de recuperação, chave SSH testada, regras
compatíveis com Docker e rollback.

## Instalar aplicação em uma conta Linux específica
O catálogo inicial para instalação no usuário via `pipx` permite `httpie`,
`poetry` e `ansible`. As aplicações são instaladas no HOME do usuário, sem
instalar Python globalmente. Primeiro preparar pipx:

```bash
sudo apt-get install -y pipx
```

Exemplo de planejamento (nenhuma alteração):
```bash
sudo python3 security/install-user-app.py --user alice --app poetry
```

Aplicar depois de revisar:
```bash
sudo python3 security/install-user-app.py --user alice --app poetry --apply
```

A conta deve ser regular, com HOME convencional em `/home/USER`. Não aceita
nomes arbitrários de pacotes nem strings shell, não roda como root dentro
do ambiente do usuário. Ainda falta expor a ação na interface por um executor
com privilégios isolados e logs de auditoria.

## Sessão root que faz túnel
Uma conexão `ssh -N -L ... root@servidor` pode não produzir uma entrada
em `who` ou `loginctl list-sessions`. O painel tenta apresentar
`sshd` associado, mas não garante identificação de todas as conexões.
O login root no *painel* continua proibido; o hardening futuro bloqueará
root por SSH quando houver acesso alternativo validado.
