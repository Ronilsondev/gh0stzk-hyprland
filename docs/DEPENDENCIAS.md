# Dependências e matriz de integração

O manifesto executável é `packages.json`; tudo que entrega a experiência padrão
é obrigatório. `--optional` fica para Bluetooth, uwsm e ShellCheck. Bateria,
backlight e Bluetooth só têm dados/ações úteis quando existe o hardware.

| Recurso | Pacote/origem | Configuração | Inicialização |
|---|---|---|---|
| Compositor | hyprland 0.56+ | config/hyprland.lua → current/theme.lua | wrapper / entrada Wayland |
| Barras, inclusive seis painéis de Pamela e Z0mbi3 vertical | waybar | current/waybar.json + waybar.css | gh0stzk session; watcher de monitores |
| Wallpaper | swaybg; wallpapers incluídos | current/wallpaper.* | processo gerenciado wallpaper |
| Notificações | dunst | current/dunstrc | processo gerenciado, verifica dono D-Bus |
| Launcher/menus | rofi 2+ | current/rofi/*.rasi; icon-theme do tema | atalhos/botões sob demanda |
| Terminal | kitty | current/kitty.conf | Super+Enter → app terminal --config |
| Perfil/player/guia de atalhos | **eww** Wayland, gtk-layer-shell | cópia estável de current/eww por sessão | daemon gerenciado; botões abrem widgets |
| Seletor de cores | **hyprpicker** | controlador colorpicker | botão do painel |
| Atualizações | **pacman-contrib** | controlador status updates | consulta do painel/checkupdates |
| GTK 3 | **gh0stzk-gtk-themes**, gsettings-desktop-schemas | perfil privado GTK/GSettings | wrapper e troca de tema |
| Ícones | **coleções gh0stzk**, papirus-icon-theme, adwaita-icon-theme | GTK, Rofi e Dunst | seleção do tema |
| Cursor | **gh0stzk-cursor-qogirr**, adwaita-cursors | XCURSOR_THEME/PATH; hyprctl setcursor | wrapper + troca de tema |
| Fontes | ttf-jetbrains-mono-nerd, ttf-inconsolata, ttf-terminus-nerd, Maple incluída | Kitty, CSS, Rasi, Dunst e GTK | fontconfig/fc-cache |
| Bloqueio/inatividade | hyprlock, hypridle | current/hyprlock.conf e hypridle.conf | daemon idle; atalho/menu |
| Áudio/mídia | pipewire, pipewire-pulse, wireplumber, playerctl, pavucontrol | serviços + módulos | habilita serviços ausentes; ações do controlador |
| Rede | networkmanager | nmcli/nmtui | serviço existente ou habilitado; menu no Kitty |
| Captura/clipboard | grim, slurp, wl-clipboard, cliphist, xdg-user-dirs | controlador + processos wl-paste | sessão e atalhos |
| Portais/polkit | xdg-desktop-portal, backends hyprland/gtk, hyprpolkitagent | preferência Hyprland; D-Bus | ativação D-Bus e agente sem duplicação |
| Downloads/build | curl, git, zstd, base-devel, rust, gtk3, libdbusmenu-gtk3, librsvg | visuals.json; tools/eww/PKGBUILD | instalador, como usuário comum |

## Eww

Primeiro preserva o Eww já instalado; se ausente, consulta o pacote oficial.
Se não estiver nos repositórios sincronizados, compila a receita local
`tools/eww/PKGBUILD` com `makepkg` **sem sudo**, a partir do upstream v0.6.0
(MIT), arquivo fonte com SHA-256 e Cargo.lock. Só `pacman -U` usa sudo. Não
instala helper nem executa uma receita AUR obtida dinamicamente.
`--with-eww ARQUIVO` continua aceitando um pacote local já compilado.
Falhas interrompem a instalação. A aceitação de Yuck/SCSS pelo Eww instalado
é verificada ao iniciar o daemon e listar os widgets; a aparência exige VM.

## Recursos externos

Origem: [gh0stzk/pkgs](https://github.com/gh0stzk/pkgs), revisão
`b8a1a288c6b8b4a061ac6f5a5194221a871b96ca`. Disponibilidade e hashes dos 15
arquivos de dados foram conferidos nesta investigação. `visuals.json` fixa URL,
SHA-256 e licença declarada GPL3 de cada `.PKGINFO`; o repositório tem LICENSE
GPL-3.0. Essa declaração não é uma auditoria individual de autoria de cada
ícone derivado. Os arquivos externos não são redistribuídos neste projeto.

Inclui 18 temas GTK, Qogirr/Qogirr-Dark e BeautyLine, Candy, Catppuccin-Mocha,
Dracula, Glassy, Gruvbox-Plus-Dark, Hack, Luv-Folders, Sweet-Rainbow,
TokyoNight-SE, Vimix-White, Zafiro e Zafiro-Purple. **Candy é necessária por
herança**, inclusive para BeautyLine, Glassy e Sweet-Rainbow.

Não adiciona repositório HTTP nem altera SigLevel. Extrai somente dados em
`~/.local/share/gh0stzk-hyprland-visuals/<revisão>/share`, sem executar scripts.
O wrapper adiciona esse caminho à busca **desta sessão**. A publicação do link
`current` só ocorre após conferir todos os recursos principais e heranças.
Downloads com erro/hash diferente interrompem a instalação.

Os arquivos originais têm links quebrados e links absolutos para a home do
criador (principalmente Glassy). Links que saem da árvore são omitidos; os
nomes exatos ficam em `current/report.json` (`omitted_links`, `broken_links`).
Esses ícones individuais ficam incompletos e podem usar a herança do tema.
O instalador informa essa limitação e não anuncia equivalência visual integral.
GTK 4/libadwaita não tem tema original correspondente nesses arquivos: o perfil
seleciona ícones/fontes/cursor, mas não promete reproduzir CSS GTK 3 em libadwaita.

## Fontes e limitações explícitas

A instalação padrão disponibiliza Maple e fontes oficiais licenciadas. Nomes
antigos JetBrainsMono NF/JetBrains Mono foram normalizados. Material Design
Icons/Meslo dos arquivos originais usam a família JetBrainsMono Nerd Font nos
renderizadores; Scientifica usa Terminess Nerd Font Mono. Isso mantém os glifos
Nerd Font usados pela adaptação, mas métricas/desenho precisam de comparação
na VM e não são apresentados como reprodução tipográfica exata. Fontes sem
licença individual no upstream não são copiadas.

`--without-fonts`, `--without-portals` e `--without-session` são exclusões
explícitas, não o padrão completo: podem deixar fontes/integração/entrada
indisponíveis. `widgets: false` é respeitado em atualizações; removê-lo ou usar
`true` reativa os widgets. As preferências do usuário não são sobrescritas.
