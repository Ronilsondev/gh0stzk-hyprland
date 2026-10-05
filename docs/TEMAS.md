# Temas e identidade visual

Inventário derivado de `config/bspwm/rices/*` no commit registrado em `UPSTREAM.json`.
A prévia de cada tema foi composta em `docs/references/temas-originais.jpg` para comparar enquadramento, barras e wallpaper. O arquivo `preview.webp` e todos os wallpapers foram mantidos byte a byte. As geometrias e módulos Polybar alimentam o renderizador Waybar; os painéis passam a camadas Wayland independentes.

| Tema | Painéis originais | Composição preservada no Waybar | Paleta / wallpaper default | Wallpapers | Estado |
|---|---:|---|---|---:|---|
| aline | 1 | 1 barra superior, largura 82%, offset horizontal 9%; módulos centrais sim | Rose Pine Dawn; `walls/wall-01.webp` | 8 | Estático passou; gráfico pendente |
| andrea | 0 | Eww horizontal, barra flutuante com workspaces no centro, popup inferior de áudio | paleta própria; `walls/wall-01.webp` | 10 | Estático passou; gráfico pendente |
| brenda | 1 | 1 barra superior, largura 98%, offset horizontal 1%; módulos centrais não | Everforest; `walls/wall-02.webp` | 7 | Estático passou; gráfico pendente |
| cristina | 1 | 1 barra inferior, largura 95%, offset horizontal 2.5%; módulos centrais não | Rose-Pine Moon; `walls/wall-01.webp` | 8 | Estático passou; gráfico pendente |
| cynthia | 2 | 2 barras horizontais: superior/inferior | Kanagawa Dragon; `walls/wall-06.webp` | 10 | Estático passou; gráfico pendente |
| daniela | 1 | 1 barra superior, largura 100%, offset horizontal 0; módulos centrais sim | Catppuccin Mocha; `walls/wall-02.webp` | 10 | Estático passou; gráfico pendente |
| emilia | 1 | 1 barra superior, largura 90%, offset horizontal 5%; módulos centrais sim | Tokyo Night; `walls/wall-01.webp` | 12 | Estático passou; gráfico pendente |
| h4ck3r | 1 | 1 barra superior, largura 100%, offset horizontal 0; módulos centrais sim | Hack The box; `walls/wall-01.webp` | 8 | Estático passou; gráfico pendente |
| isabel | 1 | 1 barra inferior, largura 100%, offset horizontal 0; módulos centrais sim | Onedark; `walls/wall-04.webp` | 7 | Estático passou; gráfico pendente |
| jan | 1 | 1 barra superior, largura 100%, offset horizontal 0; módulos centrais sim | CyberPunk; `walls/wall-01.webp` | 7 | Estático passou; gráfico pendente |
| karla | 3 | 3 barras superiores para launcher/workspaces, media e dados | Zombie-Night; `walls/wall-01.webp` | 7 | Estático passou; gráfico pendente |
| marisol | 1 | 1 barra superior, largura 100%, offset horizontal 0; módulos centrais sim | Dracula; `walls/wall-01.webp` | 8 | Estático passou; gráfico pendente |
| melissa | 2 | 2 barras horizontais: superior/inferior | Nord; `walls/wall-01.webp` | 11 | Estático passou; gráfico pendente |
| pamela | 6 | 6 barras superiores independentes: launcher (2,5%), workspaces (17%), música (22%), indicadores (26,5%), relógio/energia (10%) e rede/clima/tray (15,5%) | Lovelace; `walls/wall-01.webp` | 9 | Estático passou; gráfico pendente |
| silvia | 1 | 1 barra superior, largura 100%, offset horizontal 0; módulos centrais não | Gruvbox; `walls/wall-01.webp` | 9 | Estático passou; gráfico pendente |
| varinka | 1 | 1 barra superior, largura 96%, offset horizontal 2%; módulos centrais não | Monochrome; `walls/wall-11.webp` | 11 | Estático passou; gráfico pendente |
| yael | 1 | 1 barra superior, largura 98%, offset horizontal 1%; módulos centrais sim | OxoCarbon; `walls/wall-01.webp` | 7 | Estático passou; gráfico pendente |
| z0mbi3 | 0 | Eww vertical à esquerda (90% de altura), com painel e controles | Decay, decayce variant; `walls/wall-05.webp` | 12 | Estático passou; gráfico pendente |

## Particularidades

- **Emilia** é a referência arquitetural: paleta Tokyo Night, barra flutuante com largura de 90%, seleção de workspaces nativa, Kitty/Rofi/Dunst/Hyprlock coordenados e os doze wallpapers originais.
- **Pamela** conserva seis painéis superiores independentes para compor a grade original. Em 1600×900 isso fica próximo do exemplo; em escalas maiores, os mínimos de fonte/módulos podem causar sobreposição.
- **Karla** conserva três barras com as separações para workspace, player de mídia e medidores.
- **Cynthia** e **Melissa** conservam duas barras e a orientação top/bottom. Melissa mantém a barra superior muito preenchida e a inferior decorativa/media.
- **Isabel** e **Cristina** mantêm a barra inferior. Os módulos internos `bspwm` passam a `hyprland/workspaces`, nome/título passa ao estado Hyprland e espaços são calculados por saída.
- **z0mbi3** mantém barra vertical Wayland à esquerda, imagem lateral e módulos em orientação vertical.
- **Andrea** manteve o esqueleto horizontal flutuante e os ícones originais de seu Eww-bar; os controles de música/estado são Waybar ou widgets no lugar de listeners `bspc`.
- As demais barras horizontais retêm número de painéis, módulos, posição, offsets, cor, fonte, raio e ordem esquerda/centro/direita da configuração Polybar.
- Efeitos Picom tornam-se rounding, blur, sombra e animações do Hyprland. O valor de borda BSPWM era `0` em todas as paletas; a cor focada e normal permanece configurada para uma largura personalizável pelo editor.

Todos os temas são **gerados e passaram por validação estática individual**. Nenhum tema foi testado numa sessão gráfica Hyprland. Veja [validação](VALIDACAO.md), [composição de referência](references/temas-originais.jpg) e [limitações](MIGRACAO.md).
