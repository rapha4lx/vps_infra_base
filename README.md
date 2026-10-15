# VPS Infra Base — VPS Control (development branch)

Painel de controle multiusuário para VPS Ubuntu/Debian, com autenticação PAM,
inventário Podman rootless, integração planejada com Traefik central e ferramentas
de segurança. **Este projeto ainda é protótipo e não deve ser usado em produção
sem revisão de segurança e testes em VM descartável.**

## Fluxo padrão alterado

`make install` ou `sudo bash setup.sh` instala o painel no host usando systemd,
com bind `127.0.0.1:8083`. Não cria rede Docker e **não instala nem inicia**
Nginx, PostgreSQL ou RabbitMQ.

A antiga stack foi movida para `legacy/docker-compose.yml` apenas para
referência/migração: nenhum volume ou container existente será apagado pelo
instalador.

## Instalação em ambiente de homologação

```bash
git checkout feat/vps-control-panel
sudo bash setup.sh
# Se não existir uma conta humana, o instalador pedirá usuário e senha
# Se já existir, autorize uma conta confiável explicitamente:
sudo usermod -aG vps-panel-admins SEU_USUARIO_LINUX_EXISTENTE
```

A partir do computador local:
```bash
ssh -L 8083:127.0.0.1:8083 SEU_USUARIO@HOST
```

Abra `http://127.0.0.1:8083` e entre com login/senha PAM de uma conta Linux
não-root autorizada. Não exponha 8083 diretamente à internet.

```bash
make status
make logs
make test
```

## Componentes atuais

- `control-panel/`: interface FastAPI, inventário, métricas e status básico;
- `podman-monitor/`: monitor de eventos e Quadlets rootless;
- `network-gateway/`: protótipo gateway Traefik → portas host loopback;
- `traefik-routing/`: validador de labels e compilador de rotas autorizadas;
- `security/`: instalador baseline Fail2ban/sudo/auditd;
- `tests/e2e/`: Traefik HTTPS → backend Docker descartável.

## Bloqueios para produção

O backend ainda roda com privilégios altos; precisa de um executor separado
com interface restrita, auditoria, revogação robusta de sessões e testes
de autorização. Integração de rede privada entre Traefik e Podman, persistência
das regras nftables, aprovação de publicação, gerenciamento de containers
pelo painel e testes de reboot **não estão concluídos**. O smoke test Traefik
atual utiliza Docker descartável, não prova o caminho com Podman rootless.
O instalador não modifica SSH/firewall.

A documentação adicional está em `docs/` e as propostas de integração
com Traefik em `rapha4lx/traefik`, PR #1.
