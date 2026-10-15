# Boot automático de containers Podman rootless

## Requisito obrigatório
Containers de usuários devem iniciar após reboot da VPS sem login interativo. Eles devem continuar operando após logout. Requer persistência de armazenamento, serviços habilitados e política de reinício.

## Implementação
1. Instalar Podman, uidmap, slirp4netns/pasta conforme distro, e suporte a systemd user.
2. Para cada conta gerenciada com permissão de containers, assegurar subuid/subgid adequados, home persistente, e executar `loginctl enable-linger <usuario>` como root por helper com argumento validado.
3. Declarar cada workload como Quadlet em `~/.config/containers/systemd/<app>.container`, sob propriedade do usuário; arquivo com seção `[Install]` e `WantedBy=default.target`.
4. Aplicar `systemctl --user daemon-reload` e `systemctl --user enable --now <app>.service` no contexto do usuário, com `XDG_RUNTIME_DIR=/run/user/<uid>` e bus acessível.
5. Em cada Quadlet, configurar `[Service]` com `Restart=always` e `RestartSec=5` quando apropriado. Configurar healthchecks e limites de recursos. Não depender de `podman start` dentro de `rc.local`, cron @reboot ou scripts de login.
6. UI exibe estados: boot_enabled, restart_policy, active, last_exit, health, logs; oferece iniciar, parar, reiniciar, habilitar/desabilitar boot e atualizar.
7. Desativar linger apenas com decisão explícita quando não houver workloads persistentes restantes; não apagar serviços de outros projetos do usuário.

## Exemplo (executado como usuário dono)
Arquivo: `~/.config/containers/systemd/demo.container`

```ini
[Unit]
Description=Demo Podman rootless
[Container]
Image=docker.io/library/nginx:alpine
ContainerName=demo
PublishPort=127.0.0.1:18080:80
[Service]
Restart=always
RestartSec=5
[Install]
WantedBy=default.target
```

Como root, uma vez por usuário:

```bash
loginctl enable-linger alice
loginctl show-user alice -p Linger
```

Como alice (em uma sessão systemd de usuário válida):

```bash
systemctl --user daemon-reload
systemctl --user start demo.service
systemctl --user status demo.service
```

**Nota:** habilitação de Quadlet se dá pela seção `[Install]` processada pelo generator no boot/reload; não presumir que `systemctl --user enable demo.service` funcione como em uma unit permanente. Testar geração e ativação sob a versão de Podman da distribuição.

## Validação obrigatória
- Provisionar duas contas distintas, ambas com linger, Quadlets e volumes persistentes.
- Reiniciar a VPS; **sem fazer login em nenhuma delas**, confirmar que ambos serviços retornaram e que seu endpoint responde.
- Sair de todas as sessões e verificar que serviços continuam ativos.
- Provocar falha controlada em container e verificar restart policy.
- Checar isolamento entre contas, roteamento Traefik, acesso ao armazenamento e ausência de portas públicas desnecessárias.
- Em caso de falha de boot, registrar diagnósticos via journalctl e mostrar no painel.
