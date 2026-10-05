# Migração dos componentes

| Original | Decisão | Implementação nesta adaptação | Diferença/limite |
|---|---|---|---|
| BSPWM / `bspc` | Adaptado | Hyprland 0.56 Lua, dispatchers, regras, workspaces, `dwindle` | A árvore binária e as regras automáticas de polaridade do BSPWM não são reproduzidas. O layout pode reorganizar as divisões; não há promessa de árvore idêntica. |
| sxhkd | Adaptado | Binds Lua nativos; teclas declaradas uma vez no compositor | O compositor recebe os atalhos; não há daemon externo. |
| Polybar | Adaptado | Waybar, em até seis superfícies independentes por tema, offsets relativos por saída, escalas e hotplug | CSS não transpõe todas as métricas de fonte/padding do Polybar. Substituições de backend para workspace/rede/áudio são próprias do Wayland. |
| Eww | Parcialmente mantido | Válvula opcional Wayland para cartões de perfil e player; GTK layer-shell, namespace isolado, estados consultados pelo controlador | Não usa barras Eww para Andrea/z0mbi3; seus assets e composição foram transplantados a Waybar. Exige build Wayland e não passou por parser nativo aqui. Os comandos/scripts X11 dos widgets originais foram removidos. |
| Picom | Substituído | Decoração/renderizador compositor: raio, borda, sombra, blur, animações | Fade e animações customizadas do Picom não têm equivalência exata; `P_FADE` não é transposto. Blur e sombras podem custar desempenho ou não ficar disponíveis no backend/GPU. |
| wallpaper X11 | Substituído | Swaybg, imagem estática selecionada do tema, tela preenchida em cada saída | Não implementados vídeo, GIF, engine animada, slideshow a cada 15 min nem imagem distinta por monitor. Hyprpaper foi evitado: API muda com versões e há uma alternativa madura para a tarefa estática. |
| i3lock-color | Substituído | Hyprlock, imagem, fonte e cores de entrada/relógio oriundas do tema | Não transpõe indicadores/efeitos exclusivos do i3lock-color. |
| Inatividade | Substituído | Hypridle: bloqueio em 5 min, DPMS em 10 min; bloqueio antes de suspender | Verifique os tempos e inibição de sono após instalar. `inhibit_sleep = 3` exige que o bloqueio ativo confirme o protocolo; teste sua compilação local. |
| maim / `xwininfo` | Substituído | Grim completo, Slurp por região, geometria da janela focada via Hyprland IPC, wl-copy PNG | A janela é gravada pelo seu retângulo Hyprland; decorações de compositor não são incluídas. Salva em XDG Pictures/Screenshots. Compartilhamento/portal de captura é outro caso. |
| Clipcat / xclip | Substituído | wl-clipboard + Cliphist, watchers separados para texto e imagem | Clipboard persistente do Cliphist pertence ao usuário; limpe com `cliphist wipe`. Conteúdo de imagem pode ficar maior. |
| Rofi | Mantido após checagem | Rofi 2.0 Wayland upstream, CSS/Rasi original, launcher, seletores, energia e escolhas | A opção de lista retorna índices controlados; não se executam linhas de saída do menu. A integração `-show window` dependente de X não substitui o switcher: lista consultada via Hyprland IPC. Requires Rofi 2.x. |
| Dunst | Mantido após checagem | Backend Wayland, cores/origem/fonte por tema e limite de instância externa | Efeito Picom e presets de animação de notificações foram omitidos. Se outro daemon já detém `org.freedesktop.Notifications`, a sessão informa conflito e não encerra o processo alheio. |
| Kitty | Mantido | Arquivo de cores por geração, paleta de 16 cores, fonte, opacidade e comportamento Kitty Wayland | Só os processos abertos com o `kitty.conf` desta adaptação recebem SIGUSR1; configurações globais não são alteradas. Outros terminais configurados não herdam o tema automaticamente. |
| Eww/Polybar system tray | Nativo Wayland | módulo `tray` Waybar por saída | Plugins e ações do tray são dos próprios aplicativos. |
| jgmenu / botão direito com `xdotool`/xprop | Substituído | Launcher e comandos explicitamente expostos em Rofi/Waybar | Não inspeciona a janela sob o cursor via X11. O comportamento do jgmenu `desktop` não é equivalente. |
| `xrandr` / MonitorSetup | Substituído | Regra padrão Hyprland por saída descoberta, escala auto, posição auto, IPC no hotplug, `hyprctl monitors all` | Sem valores pessoais de monitor/interface. Modos, posição e escalas específicas pertencem a `local.lua`. |
| `xdotool`, `wmctrl`, `xprop` | Substituído | `hyprctl -j monitors/clients/activewindow`, dispatchers, XDG shell | Campos X11 inexistentes não são inferidos; apps XWayland seguem compatibilidade herdada quando necessários. |
| NetworkManager applet | Adaptado | nmtui em terminal flutuante, requer NetworkManager e dispositivo habilitado | O caminho simples de controle seleciona nmtui; não reimplementa todas as operações do NetManagerDM original em Rofi. |
| Bluetooth rofi script | Adaptado | Blueman Manager sob demanda e indicador Waybar quando dispositivo acessível | Exige BlueZ, serviço, adaptador e pacote Blueman opcionais. Não fixa interface/endereço. |
| `pamixer` / `playerctl` | Adaptado | `wpctl` e playerctl pelos dispositivos/sessão disponíveis; teclas XF86 bloqueadas preservadas | Mixer visual exige Pavucontrol. Funções de MPD permanecem disponíveis quando MPD apresenta MPRIS/Playerctl. |
| brilho / bateria | Adaptado | brightnessctl em `/sys/class/backlight`; Waybar detecta battery sem nome fixo | Sem hardware, o módulo pode permanecer ausente e brilho retorna mensagem. Desktop não inventa uma bateria em PC de mesa. |
| agente polkit | Integrado com detecção | Serviço usuário `hyprpolkitagent` opcional; verifica agentes conhecidos | Não inicia serviço se um agente conhecido já está ativo. Confirme apps gráficas que pedem autenticação. |
| portal de desktop / screen share | Integrado sem duplicar | preferência opcional `hyprland-portals.conf`, backend Hyprland e fallback GTK; sessão atualiza ambiente D-Bus | Não inicia serviço de portal. PipeWire, backend Hyprland e portal GTK devem ser instalados; configure um backend ativo. Teste compartilhamento e seletor de arquivos em apps reais. |
| `RiceEditor` | Adaptado parcialmente | `Super+R` edita por tema borda, raio, blur, sombras, animações e opacidade, com rollback se falhar | Paleta, CSS de cada módulo, alinhamento e configurações de widgets ainda são editados nos JSON/CSS/Yuck em ferramentas de texto. Não foi reproduzida uma UI genérica de todos os campos. |
| alternador de fontes/temas GTK global | Não copiado automaticamente | cores Waybar/Rofi/Dunst/Hyprlock/Kitty e fontes originais; GTK nomeado por tema | Os temas GTK/cursor/ícones extras vêm do repositório de pacotes externo do upstream, fora do clone original. Não adicionamos trust/repositório sem auditoria. |
| shell, Neovim, Firefox, Geany, ncmpcpp | Preservado sem alteração | Recursos e documentos originais ficam na cópia `upstream/`; nenhum arquivo da aplicação entra no `~/.config` | A sessão não ativa módulos de cor de aplicativos que não foram instalados nesta camada. Editor pode apontar a Geany, mas nenhuma config Neovim é copiada. |

## Wayland e serviços externos

Rofi 2.x tem backend oficial Wayland; Polybar tem como alvo BSPWM/X11 e é
substituído por Waybar; Dunst suporta layer-shell Wayland e não é forçado em
XWayland. Eww suporta layer-shell, com opções de stacking/namespace/exclusividade
próprias do Wayland. A compatibilidade compilada de Eww permanece opt-in porque
um pacote genérico AUR pode ser construído sem backend Wayland.

`xdg-desktop-portal-hyprland` implementa interfaces usadas por picker/captura e
screen share com PipeWire; `xdg-desktop-portal-gtk` implementa fallback de file
chooser. Não mantenha simultaneamente portais Hyprland, KDE e GNOME em autostarts
duplicados. Confira o estado por D-Bus/systemd do seu ambiente antes de mudar a
preferência. Não copie `dbus-update-activation-environment --systemd` para um
segundo autostart; o próprio Hyprland/gerenciador de sessão pode já fazer isso.

Um aplicativo X11 pode abrir via XWayland, mas nenhum binding, compositor,
notificação, barra, wallpaper ou automação migrada depende de `bspc`, `xrandr`,
`xdotool`, `wmctrl`, `xprop`, `xwininfo`, `feh`, Picom ou sxhkd.
