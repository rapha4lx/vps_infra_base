# Estado executável do protótipo VPS Control

> **Não aplicar diretamente em uma VPS de produção.** Esta branch ainda
> contém recursos incompletos e o daemon administrativo precisa de
> isolamento e revisão de segurança antes de exposição remota.

## Entregue nesta branch
- API FastAPI no loopback 127.0.0.1:8083 com PAM e grupo explícito vps-panel-admins.
- Sessões em memória, expiração, CSRF e limitação básica de login.
- Leitura de contas, grupos e sessões; criação de contas e grupos,
  membership não-privilegiado.
- Inventário read-only de caches de agentes rootless.
- Monitor Podman por usuário com eventos + reconciliação, unit systemd user.
- Script de provisionamento de linger, sem modificar SSH.
- Validador de labels de roteamento e gerador de intenção de rota.
- Script baseline de Fail2ban e pacotes de segurança.
- Workflow CI de sintaxe, unidades e shell.

## Instalação apenas em ambiente descartável/homologação
Pré-requisitos: Ubuntu/Debian com systemd, Python 3, console de emergência,
conta SSH com chave funcionando, snapshot e rede privada.

```bash
git checkout feat/vps-control-panel
sudo bash security/install-base.sh
sudo bash control-panel/install.sh
# Use uma conta Linux EXISTENTE, não-root e de sua confiança:
sudo usermod -aG vps-panel-admins ADMIN_USER
# Verifique que o serviço está somente em loopback:
sudo ss -lntp | grep ':8083'
sudo systemctl status vps-panel
```

A partir do notebook:
```bash
ssh -L 8083:127.0.0.1:8083 ADMIN_USER@VPS_HOST
```
Acesse http://127.0.0.1:8083. O usuário precisa ter senha PAM válida
e pertencer a `vps-panel-admins`. SSH por chave e senha PAM web são
mecanismos distintos.

Para um usuário rootless:
```bash
sudo apt-get install -y podman uidmap
sudo bash podman-monitor/provision-user.sh USER
sudo install -D -m 0755 podman-monitor/monitor.py /opt/vps-infra-base/podman-monitor/monitor.py
```
Em sessão **real** do usuário:
```bash
bash podman-monitor/install.sh
systemctl --user daemon-reload
systemctl --user enable --now vps-podman-monitor.service
python3 /opt/vps-infra-base/podman-monitor/monitor.py --once
```
A instalação desse monitor requer que o diretório do script seja
acessível ao usuário e que `podman` funcione rootless.

## Lacunas bloqueantes antes de produção
1. O backend administrativo ainda roda com privilégios elevados:
   migrar para conta de serviço sem root com broker limitado e auditoria.
2. Armazenamento de sessão em memória sem persistência/revogação distribuída.
   Rate limiting local básico não substitui controle de brute force do painel.
3. Terminal PTY seguro, gestão/revogação de sessões systemd-logind e
   instalador de catálogo **não estão implementados**.
4. Conexão isolada Traefik Docker ↔ Podman rootless, política nftables,
   aprovação de domínio e montagem dinâmica de rotas **não implementadas**.
5. Adoção de containers externos para Quadlet é manual; não converter
   automaticamente. Reinício após boot requer Quadlet válido e linger.
6. Não há enforcement de quotas de storage/CPU/memória nem backups automáticos.
7. SSH hardening e UFW precisam de pré-validação e rollback; nada disso é
   habilitado automaticamente.
8. Testes de integração em Ubuntu/Debian, teste de reboot sem login,
   revisão de permissões e operação real do Traefik ainda pendentes.
9. Reconciliar origem e integridade dos arquivos cache antes de considerá-los
   fatos de segurança; um usuário pode editar seu próprio inventário.

## Política de exposição
Nenhuma porta de app deveria estar acessível externamente fora de
Traefik. Restrições de publicação Podman devem ser impostas no host
(nftables/namespace/gateway) e testadas, não apenas no painel.
Atualmente o projeto **não garante** isso.
