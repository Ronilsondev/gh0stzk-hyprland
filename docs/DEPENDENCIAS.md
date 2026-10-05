# Dependências e compatibilidade

`packages.json` é a fonte única. Ele separa **oficiais obrigatórios**,
**oficiais opcionais**, **AUR opcional** e **recursos fora deste repositório**,
e é validado por `tools/bootstrap.py` antes de qualquer transação do `pacman`.

## Nomes de pacote conferidos no catálogo oficial do Arch

Consulta de 05/10/2026 em `archlinux.org/packages`. Todos os itens de
`official` e `official_optional` existem nos repositórios `core`/`extra` com esses
nomes exatos:

| Pacote | Repositório | Versão no catálogo |
|---|---|---|
| hyprland | extra | 0.56.2 |
| waybar | extra | 0.15.0 |
| rofi | extra | 2.0.0 |
| dunst | extra | 1.13.2 |
| swaybg | extra | 1.2.2 |
| hyprlock | extra | 0.9.6 |
| hypridle | extra | 0.1.8 |
| kitty | extra | 0.49.2 |
| thunar | extra | 4.20.10 |
| firefox | extra | 157.0 |
| pavucontrol | extra | 6.2 |
| grim / slurp | extra | 1.5.0 |
| wl-clipboard | extra | 2.3.0 |
| cliphist | extra | 0.7.0 |
| brightnessctl | extra | 0.5.1 |
| playerctl | extra | 2.4.1 |
| pipewire / pipewire-pulse | extra | 1.6.9 |
| wireplumber | extra | 0.5.18 |
| xdg-desktop-portal | extra | 1.22.1 |
| xdg-desktop-portal-hyprland | extra | 1.4.1 |
| xdg-desktop-portal-gtk | extra | 1.15.3 |
| hyprpolkitagent | extra | 0.2.0 |
| networkmanager | extra | 1.58.1 |
| libnotify | extra | 0.8.8 |
| python | core | 3.14.7 |
| lua | extra | 5.5.1 |
| procps-ng | core | 4.0.7 |
| ttf-jetbrains-mono-nerd | extra | 3.5.1 |
| ttf-inconsolata | extra | 3.000 |
| ttf-terminus-nerd | extra | 3.5.1 |
| papirus-icon-theme | extra | 20260801 |
| webp-pixbuf-loader | extra | 0.2.7 |
| git | extra | 2.56.0 |
| curl | core | 8.22.0 |
| fontconfig | extra | 2.18.3 |
| dbus | core | 1.16.2 |
| mesa | extra | 26.2.4 |
| xdg-utils | extra | 1.2.1 |
| adwaita-icon-theme / adwaita-cursors | extra | 50.0 |
| blueman / bluez / bluez-utils | extra | 2.4.6 / 5.87 / 5.87 |
| hyprpicker | extra | 0.4.7 |
| pacman-contrib | extra | 1.13.1 |
| uwsm | extra | 0.27.0 |
| shellcheck | extra | 0.11.0 |

Itens que o pacote `hyprland` realmente entrega e que esta adaptação usa:
`/usr/bin/Hyprland`, `/usr/bin/hyprctl`, `/usr/bin/start-hyprland` e
`/usr/share/wayland-sessions/hyprland.desktop`. `hyprpolkitagent` e `hypridle`
instalam unidade de usuário em `/usr/lib/systemd/user/`, e `xdg-desktop-portal-hyprland`
instala `/usr/share/xdg-desktop-portal/hyprland-portals.conf`.

Como a versão se move todo dia, confira no Arch de destino antes de instalar:

```bash
pacman -Si hyprland waybar rofi dunst hyprlock hypridle kitty swaybg cliphist
Hyprland --version && rofi -version && waybar --version
```

O ambiente de desenvolvimento desta cópia **não é Arch puro** (é uma base
BigLinux/Manjaro) e não tem Hyprland, Waybar, Rofi, Dunst, Eww, Hyprlock nem
Hypridle instalados. As versões acima vieram do catálogo web do Arch, não de
`pacman -Si` local.

## Compatibilidade da configuração Lua

`luac -p` prova apenas que o arquivo é Lua válido. **Não prova compatibilidade
com o Hyprland.** Quem valida a configuração de verdade é o parser do próprio
compositor:

```bash
Hyprland --verify-config --config ~/.local/share/gh0stzk-hyprland/config/hyprland.lua
```

O instalador roda exatamente esse comando, para os 18 temas, com `HOME`
temporária e `XDG_CONFIG_HOME` isolados, e **interrompe** se falhar. Também
confere a versão reportada por `Hyprland --version` e exige 0.56 ou posterior
(`Hyprland`, `rofi` são verificados por `install.py`).

A configuração usa a API Lua do Hyprland 0.56 conferida no fonte da tag
`v0.56.2`: `hl.config`, `hl.monitor` com `reserved_area`, `hl.bind`,
`hl.dsp.*`, `hl.window_rule`, `hl.env`, callbacks `hyprland.start` e a opção de
linha de comando `--verify-config`. Veja [FONTES.md](FONTES.md).

## AUR: apenas Eww, e só se você compilar

`eww` **não existe nos repositórios oficiais do Arch** (consulta de 05/10/2026).
No AUR ele está em `aur.archlinux.org/packages/eww`, versão 0.6.0, mantido por
terceiros. Esta adaptação:

- não instala `paru`, `yay` nem qualquer helper AUR;
- não compila nada como root;
- só aceita `eww` por `--with-eww ARQUIVO`, e o arquivo precisa ser um pacote
  `eww` de nome correto, que você compilou antes como usuário comum — instalado
  com `sudo pacman -U`, sem `--noconfirm`.

O nome do pacote no AUR não garante os recursos da compilação. Os widgets usam
`exclusive`, `focusable` e `namespace`; não usam `wm-ignore`, `windowtype` nem
`struts`, que são de X11. Sem Eww, o desktop continua completo: o cartão de
perfil e os controles de música caem para alternativas em Rofi
(`preferences.json` com `"widgets": false`, ou a ausência do binário). O
instalador avisa qual dos dois caminhos está em uso.

## Recursos do autor fora deste repositório

Temas GTK, cursor e coleções de ícones vêm do repositório de pacotes do autor,
declarado no `RiceInstaller` dele como:

```
[gh0stzk-dotfiles]
SigLevel = Optional TrustAll
Server = http://gh0stzk.github.io/pkgs/x86_64
```

Ou seja, HTTP puro e **sem verificação de assinatura** (`Optional TrustAll`).
Não é possível verificar a integridade desses pacotes, e adicionar esse
repositório ao `pacman.conf` colocaria o sistema inteiro nessa condição. Esta
adaptação, portanto, **não adiciona o repositório** e não promete a aparência
original. O que fica instalado em vez disso:

| Recurso do autor | Alternativa oficial instalada |
|---|---|
| `gh0stzk-gtk-themes` | `adwaita-icon-theme` + `adwaita-cursors` |
| `gh0stzk-cursor-qogirr` | `adwaita-cursors` |
| `gh0stzk-icons-beautyline`, `-tokyo-night`, `-zafiro`, `-zafiro-purple`, `-candy`, `-catppuccin-mocha`, `-dracula`, `-glassy`, `-gruvbox-plus-dark`, `-hack`, `-luv`, `-sweet-rainbow`, `-vimix-white` | `papirus-icon-theme` + `adwaita-icon-theme` |
| `st-gh0stzk` | `kitty` |

Os nomes originais são preservados em `themes/*/theme.json` e em
`hyprland-portals.conf`, então quem instalar os pacotes auditados por conta
própria recupera a aparência desejada. `preferences.json` com
`"gtk_environment": true` aplica o nome do tema GTK ao gerenciador de arquivos
iniciado pelo controlador, sem tocar nas preferências GTK globais.

Os wallpapers, prévias, paletas, fontes incluídas, Rofi, Waybar, Dunst,
Hyprlock, Hypridle e a entrada de sessão **não** dependem desse repositório
externo: estão vendorizados neste repositório e com hash em `resources.json`.

## Portas e serviços

O instalador **inspeciona antes de habilitar** e só habilita o que não existe:

- rede: recusa continuar se `systemd-networkd`, `dhcpcd`, `iwd`, `connman`,
  unidades por interface ou `/etc/systemd/network/*.network` estiverem em uso,
  para você decidir a integração com o NetworkManager;
- áudio: recusa se `pulseaudio`, `pipewire-media-session`, `pulseaudio.socket`
  ou `pulseaudio.service` estiverem presentes ou mascarados;
- Bluetooth: apenas relata o estado; só é habilitado por decisão sua.

Nenhum serviço existente é reiniciado, desabilitado ou substituído. Só
`NetworkManager.service` (sistema) e `pipewire.socket`,
`pipewire-pulse.socket`, `wireplumber.service` (usuário) são habilitados, e
apenas se ainda não estiverem ativos ou habilitados.

Confira depois, conforme o hardware:

```bash
systemctl status NetworkManager bluetooth
systemctl --user status pipewire pipewire-pulse wireplumber
```
