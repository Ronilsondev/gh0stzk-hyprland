# Licença e créditos

## Projeto de origem

**gh0stzk**, Copyright © 2021–2026,
<https://github.com/gh0stzk/dotfiles>, GPL-3.0.

O commit exato importado está em [UPSTREAM.json](UPSTREAM.json):
`bbcd8b00e537ddad63d34a0c448e5bd539078fcb`. Esse é o único ponto de referência
para a origem dos dados; ele **não** é alterado por este projeto.

O texto integral da licença original está em `LICENSE` e permanece também na
cópia de desenvolvimento `upstream/gh0stzk-dotfiles/LICENSE`, que **não** é
publicada.

## Esta adaptação

Adaptação independente para **Arch Linux com Hyprland 0.56+**, GPL-3.0. Não há
afiliação, endosso nem alegação de suporte pelo autor original. Os scripts,
renderizadores, configurações derivadas e a documentação novos são obra desta
adaptação, sob a mesma licença.

O que vem do commit de origem: paletas, nomes e identidades dos 18 temas,
161 wallpapers, 18 prévias, arquivos de menu, configurações Rofi, estilos dos
widgets e as fontes copiadas para `assets/fonts`.

`tools/import_upstream.py` registra a proveniência e copia recursos **sem
executar script nenhum do upstream**. Os arquivos fonte originais ficam apenas
na cópia de desenvolvimento, ignorada pelo Git.

## Recursos de terceiros e licenças

Este repositório reúne material com titulares e licenças próprios. A licença
global GPL-3.0 do repositório **não** prova direito de redistribuição de cada
recurso de terceiros.

**Fontes.** Só `assets/fonts/MapleMono-NF/` é publicada, e ela traz a licença
própria em `assets/fonts/MapleMono-NF/LICENSE.txt`
(Maple Mono NF, subjacente Maple Mono). As demais fontes copiadas do upstream
(CartographCF, Cherry, Clarity City, Iosevka Nerd Font, Material Design Icons
Desktop, MesloLGS Nerd Font, Phosphor, Sci-Fi, FontAwesome, Bebas Neue) estão
**fora do repositório e fora da instalação**: `.gitignore` e `install.py` aplicam
a mesma regra. O upstream não fornece licença individual para cada uma delas, e
o bootstrap instala Maple por padrão (`--without-fonts` é exclusão explícita). Nenhuma fonte paga foi
obtida de outra fonte.

**Wallpapers e prévias.** Vêm do commit de origem. O upstream não fornece
licença individual por wallpaper; o aviso do próprio repositório de origem
aplica-se. Confira antes de redistribuir um pacote público.

**Temas GTK, cursor e coleções de ícones.** Baixados na instalação a partir de
[gh0stzk/pkgs](https://github.com/gh0stzk/pkgs), revisão e SHA-256 fixados em
`visuals.json`, por HTTPS. GPL3 é a licença declarada nos `.PKGINFO`, e o
repositório publica GPL-3.0; não há licença individual em todas as coleções.
Isso não constitui auditoria de todos os derivados. Não são redistribuídos
neste projeto. Extração de dados como usuário comum, sem scripts nem mudanças
em SigLevel. Links externos/quebrados são documentados no relatório instalado.
Veja [DEPENDENCIAS.md](docs/DEPENDENCIAS.md).

**Programas.** Hyprland, Hyprlock, Hypridle, hyprpolkitagent, Waybar, Rofi,
Dunst, Eww, Kitty, Swaybg, Grim, Slurp, wl-clipboard, Cliphist, NetworkManager,
PipeWire, WirePlumber e demais são dos seus autores. Nenhum binário é
redistribuído aqui e nenhuma licença deles é alterada.

## Demais

`instalar.sh`, `install.py` e as ferramentas em `tools/` foram escritos para
esta adaptação e não contêm código do upstream. As referências a `bspc`,
`sxhkd`, Polybar, Picom e comandos X11 aparecem apenas como documentação do que
foi substituído, nunca como dependência em tempo de execução.
