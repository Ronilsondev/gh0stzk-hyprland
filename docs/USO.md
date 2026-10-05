# Personalização e recuperação

`local.lua` e `preferences.json` ficam em `~/.config/gh0stzk-hyprland`.
O instalador cria apenas os ausentes; trocar tema nunca os escreve. O seletor de
estilo altera somente a preferência de estilo que você escolheu explicitamente.
O editor de aparência salva diferenças em `themes/NOME.json` dentro desse mesmo
diretório local, sem alterar os recursos importados.

Exemplo de `local.lua`:

```lua
hl.config({input = {kb_layout = 'br,us', kb_options = 'grp:alt_shift_toggle'}})
-- Obtenha a descrição real com hyprctl monitors all, depois acrescente:
-- hl.monitor({output = 'desc:DESCRIÇÃO REAL', mode = 'preferred', position = 'auto', scale = 1.25,
--             reserved_area = {top = 50, right = 1, bottom = 1, left = 1}})
```

A tabela de margens usa os campos `top`, `right`, `bottom`, `left`. A regra automática
reserva as margens originais de cada tema. Regras locais específicas de monitor
devem definir suas próprias margens quando necessário. Monitores não especificados
usam resolução preferida, escala 1 e posição automática. Não existe limite de
quatro monitores. Waybar recebe geometrias por saída, considerando escala e rotação;
o observador IPC regenera as barras em hotplug/reload. Use `gh0stzk refresh` após
mudanças se o compositor/driver não emitir o evento esperado.

As barras estreitas originais foram desenhadas para 1600×900/96 DPI. Em saídas
menores ou com escala maior, o tamanho mínimo dos módulos pode exceder a largura
original. Reduza fontes/módulos em uma cópia do tema; verifique a matriz visual
antes de usar todos os painéis em notebooks de baixa resolução.

Aplicativos em `preferences.json` são arrays de argumentos, nunca código shell.
Exemplo: `"files": ["thunar"]`. Kitty é o terminal integrado: cores/opacidade
são recarregadas apenas nos processos abertos com a configuração desta adaptação.
Um terminal alternativo pode ser selecionado com seu próprio arquivo e argumentos,
mas não recebe automaticamente a paleta. Scratchpad/flutuante integrado exige
Kitty; para outro terminal, crie a regra correspondente no `local.lua`.

`wallpaper_directory` aceita um diretório adicional com PNG/JPEG/WebP. A escolha
persiste por tema. Swaybg cobre todas as saídas; wallpapers diferentes por monitor,
vídeo e slideshow não estão implementados. O Hyprlock usa a mesma imagem escolhida.

`weather_file` aceita um JSON local `{"text":"23°C", "tooltip":"Minha cidade"}`,
produzido por um provedor de sua escolha. Sem ele, o módulo meteorológico é
ocultado. Não há localização pessoal, token de API nem cidade hardcoded.

`polkit: "auto"` verifica agentes existentes antes de iniciar o serviço de usuário
hyprpolkitagent. Use `"polkit": "external"` se sua sessão já gerencia um agente.
`clipboard: false` desativa os watchers na próxima sessão. O histórico não é
apagado ao trocar tema ou restaurar a instalação. `widgets: false` usa alternativas
Rofi. `gtk_environment: true` aplica o nome GTK apenas ao gerenciador de arquivos
iniciado pelo controlador, sem modificar preferências GTK globais.

O cliphist guarda os itens de clipboard no estado do usuário. Para limpar o
histórico manualmente: `cliphist wipe`.

Cada troca gera um diretório em `~/.local/state/gh0stzk-hyprland/generations`.
`current` aponta para o ativo e `previous` para o anterior. Use `gh0stzk rollback`
para recuperar a geração anterior completa, inclusive escolhas de aparência.
Os overrides locais do editor permanecem disponíveis para futuras aplicações;
para desfazer também a preferência, edite o JSON local do tema.

Se não conseguir abrir a sessão, prepare um tema conhecido a partir de um TTY:

```bash
~/.local/bin/gh0stzk theme emilia --offline
# Ou recupere a geração anterior sem tocar em serviços:
~/.local/bin/gh0stzk rollback --offline
```

Esse modo não testa componentes nem valida a configuração local no compositor.
O estado pode conter gerações antigas: elas são mantidas para recuperação e não
são apagadas indiscriminadamente. Inspecione e remova manualmente apenas as que
não são alvos de `current`/`previous`, fora da sessão.
