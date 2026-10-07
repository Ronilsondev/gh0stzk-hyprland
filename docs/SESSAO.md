# Atualizar e entrar na VM Arch

Use o repositório público [Ronilsondev/gh0stzk-hyprland](https://github.com/Ronilsondev/gh0stzk-hyprland).
O [README](../README.md#instalar-ou-atualizar-na-vm) mostra como baixar somente
`instalar.sh`, fixando a mesma revisão completa no download e em `--ref`.
Não é necessário transferir um pacote de `/tmp`. Mantenha sua instalação atual
e seus backups.

Na VM, dentro de uma cópia completa dessa revisão, como usuário comum. Se já estiver na sessão
gh0stzk com perfil XDG privado, saia voluntariamente e atualize pelo TTY:

```bash
bash instalar.sh --dry-run
bash instalar.sh
```

Isso atualiza o sistema Arch com `pacman -Syu --needed`, instala os componentes
obrigatórios, prepara recursos visuais e mantém backups em
`~/.local/state/gh0stzk-hyprland/backups`. `local.lua`, `preferences.json`,
overrides de temas e wallpapers escolhidos são preservados. Alterações locais
em arquivos gerenciados causam recusa explícita em vez de serem apagadas.

O tema inicial é **Emilia**; uma instalação existente mantém seu tema. O
instalador prepara a geração sem iniciar clientes na sessão atual. Nada encerra
ou reinicia o desktop. Não execute este procedimento na máquina principal.

Saia voluntariamente e escolha **Hyprland — gh0stzk**, não a entrada genérica
Hyprland nem o ambiente antigo. A entrada é registrada em
`/usr/share/wayland-sessions/gh0stzk-UID.desktop`, com caminho absoluto para o
wrapper e `--login`. Gerenciadores com suporte a sessões Wayland podem exigir
voltar à tela de seleção para reler as entradas; não substituímos o gerenciador.

Em TTY, fora de qualquer sessão gráfica:

```bash
~/.local/bin/gh0stzk-session
```

O wrapper regenera a seleção salva, configura o perfil privado e verifica o
Hyprland. Os componentes recebem os arquivos de `current`. A barra e wallpaper
aparecem ao entrar; o terminal personalizado abre com Super+Enter, o launcher
com Super+Espaço e widgets pelos botões do painel ou comandos abaixo.

## Verificação gráfica, começando por Emilia

Dentro da nova sessão:

```bash
~/.local/bin/gh0stzk theme emilia
~/.local/bin/gh0stzk app terminal
~/.local/bin/gh0stzk widget launchermenu
~/.local/bin/gh0stzk widget music
~/.local/bin/gh0stzk diagnose > ~/gh0stzk-diagnostico.json
```

Confira barra, wallpaper, terminal, launcher, notificação, ícones no Thunar,
cursor e os widgets e o guia Alt+F1. Verifique `hyprctl configerrors` localmente. Feche os
widgets com seus botões. Execute `gh0stzk refresh` duas vezes e confira no
relatório que não há cópias adicionais dos componentes. Ausência de erro de
parser não comprova layout, escala, contraste ou funcionamento dos botões.

Depois teste os outros 17 temas, usando `gh0stzk list` e `gh0stzk theme NOME`.
Em particular: Pamela tem seis painéis por monitor; Andrea composição horizontal;
Z0mbi3 painel vertical. Teste ao menos 1600×900 e a resolução/escala da VM, e
múltiplos monitores quando disponíveis. Confira áreas reservadas, sobreposição,
ícones, menus e troca sem duplicações. Prévias incluídas são do **BSPWM original**
e não servem de evidência da migração.

Logs locais: `session-start.log`, `session.log` e logs de componentes em
`~/.local/state/gh0stzk-hyprland`. Envie inicialmente apenas o JSON do diagnóstico;
veja [DIAGNOSTICO.md](DIAGNOSTICO.md).

Para recuperar, fora da sessão:

```bash
~/.local/bin/gh0stzk prepare emilia
# ou
~/.local/bin/gh0stzk rollback --offline
```

Backups de arquivos são restaurados pelo `install.py --restore CAMINHO --apply`.
Pacotes/serviços e o armazenamento separado de recursos externos permanecem;
não são removidos implicitamente. Gerações anteriores de recursos são mantidas.
