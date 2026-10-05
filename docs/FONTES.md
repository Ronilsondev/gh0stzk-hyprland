# Fontes oficiais consultadas

Todas as URLs abaixo foram abertas ou consultadas diretamente. Nenhuma URL foi
inventada.

## Hyprland

- [Hyprland v0.56.2 — fonte no repositório oficial](https://github.com/hyprwm/Hyprland/tree/v0.56.2)
  — é daqui que vieram a API Lua usada pela configuração (`hl.config`,
  `hl.monitor` com `reserved_area` e a tabela de margens
  `top`/`right`/`bottom`/`left`, `hl.bind`, `hl.dsp.*`, `hl.window_rule`,
  `hl.env`, callbacks `hyprland.start`) e a confirmação de `--verify-config`.
- [Hyprland — binds e dispatchers (documentação atual)](https://wiki.hypr.land/Configuring/Core/Binds/)
- [Hyprland — monitores](https://wiki.hypr.land/Configuring/Core/Monitors/)
- [Hyprland — janelas e regras](https://wiki.hypr.land/Configuring/Core/Window-Rules/)
- [Hyprland — regras de camadas](https://wiki.hypr.land/Configuring/Variables/#layer-rules)
- [Hypridle](https://wiki.hypr.land/Hypr-Ecosystem/hypridle/)
- [Hyprlock](https://wiki.hypr.land/Hypr-Ecosystem/hyprlock/)
- [hyprpolkitagent (wiki do Hypr-Ecosystem)](https://wiki.hypr.land/Hypr-Ecosystem/hyprpolkitagent/)

## Arch Linux

- [hyprland 0.56.2-4 — lista de arquivos](https://archlinux.org/packages/extra/x86_64/hyprland/files/)
  — confirmou `usr/bin/Hyprland`, `usr/bin/hyprctl`,
  `usr/bin/start-hyprland`, `usr/share/wayland-sessions/hyprland.desktop` e
  `usr/share/hypr/hyprland.lua`.
- [hyprpolkitagent — lista de arquivos](https://archlinux.org/packages/extra/x86_64/hyprpolkitagent/files/)
  — `usr/lib/systemd/user/hyprpolkitagent.service` e a entrada D-Bus
  `org.hyprland.hyprpolkitagent.service`.
- [hypridle — lista de arquivos](https://archlinux.org/packages/extra/x86_64/hypridle/files/)
- [hyprlock — lista de arquivos](https://archlinux.org/packages/extra/x86_64/hyprlock/files/)
- [hyprpicker — lista de arquivos](https://archlinux.org/packages/extra/x86_64/hyprpicker/files/)
- [Atualização parcial do sistema é proibida (ArchWiki)](https://wiki.archlinux.org/title/System_maintenance#Partial_upgrades_are_unsupported)
  — motivo de o instalador usar `pacman -Syu --needed` e nunca `-Sy` seguido de
  instalação.

Cada nome de pacote da seção "oficiais" de `packages.json` foi conferido no
catálogo do Arch em 05/10/2026: a lista completa, com repositório e versão, está
em [DEPENDENCIAS.md](DEPENDENCIAS.md).

## wayland-sessions

- [XDG Desktop Portal Integration / wayland-sessions](https://specifications.freedesktop.org/wayland-sessions/latest/)
- [Especificação Desktop Entry — campo Exec e códigos de campo](https://specifications.freedesktop.org/desktop-entry-spec/latest/)
  — é dela que vem a ordem de escape usada por `tools/session_admin.py`:
  primeiro a barra invertida, depois `"`, `` ` `` e `$`, e por último o `%`
  literal, duplicado como `%%`.

## Ferramentas do desktop

- [Rofi — release 2.0.0 com backend Wayland oficial](https://github.com/davatorium/rofi/releases/tag/2.0.0)
- [Rofi — man page](https://davatorium.github.io/rofi/current/rofi.1.en.html)
- [Dunst — documentação e opções Wayland](https://dunst-project.org/documentation/)
- [Waybar — configuração oficial](https://github.com/Alexays/Waybar/wiki/Configuration)
- [Kitty — config e reload por SIGUSR1](https://sw.kovidgoyal.net/kitty/conf/)
- [wl-clipboard](https://github.com/bugaevc/wl-clipboard)
- [cliphist](https://github.com/altdesktop/cliphist)
- [grim](https://gitlab.freedesktop.org/emersion/grim) e
  [slurp](https://gitlab.freedesktop.org/emersion/slurp)
- [Eww — configuração Wayland e layer-shell](https://elkowar.github.io/eww/configuration.html)
- [Eww — instalação Wayland](https://github.com/elkowar/eww/blob/master/docs/src/eww.md)

## Recursos de terceiros

- [eww no AUR](https://aur.archlinux.org/packages/eww) — versão 0.6.0,
  Url [https://github.com/elkowar/eww](https://github.com/elkowar/eww),
  consultado pela RPC pública do AUR em 05/10/2026. Não é oficial.
- [Maple Mono NF](https://github.com/subframe7536/maple-font) — a única fonte
  com licença de redistribuição incluída neste repositório
  (`assets/fonts/MapleMono-NF/LICENSE.txt`).
- Papas e permissões dos wallpapers, prévias e demais fontes: veja
  [CREDITS.md](../CREDITS.md).

## O que não foi verificado

- Nenhuma sessão Hyprland foi aberta. Camada, DRM/GL, áudio, portais, captura,
  bloqueio, inatividade e suspensão continuam **sem prova**.
- Os parsers nativos de Waybar, Rofi, Dunst, Eww, Hyprlock e Hypridle não
  existem neste ambiente de desenvolvimento. O verificador próprio confere
  delimitadores, imports, referências de imagem e tokens, e isso **não**
  substitui esses parsers.
- `shellcheck` não está instalado no ambiente de desenvolvimento; o
  `instalar.sh` foi analisado com o binário 0.11.0 baixado em `/tmp`, sem
  instalar nada no sistema.
