# Correção do caminho de instalação até o desktop

## Causas confirmadas no código

1. `config/hyprland.lua` concatenava `ctl .. 'session'`: executava um nome
   inexistente terminado em `gh0stzksession`. O callback agora executa o
   controlador com o argumento `session`, com log próprio. Um teste executa
   esse callback com Lua e depois seu comando no shell, incluindo caminhos com espaços.
2. `install.py` apenas copiava arquivos. Agora a instalação padrão gera
   `current`, persiste Emilia na primeira instalação (ou mantém a seleção
   existente) e valida a configuração a partir da **árvore instalada**.
3. `appearance.json` não era consumido pela sessão. GTK ficava desativado por
   padrão; só havia uma opção para Thunar. Agora o wrapper cria um perfil GTK e
   GSettings privado, seleciona tema/ícones/cursor e o controlador reaplica as
   escolhas nas trocas. Nenhum `gsettings set` escreve no dconf global.
4. Eww era opcional e widgets viravam menus Rofi. Agora é obrigatório, possui
   compilação Wayland como usuário comum e erros de inicialização são fatais.
   Cada sessão usa um diretório Eww estável: o caminho canônico de `current`
   muda entre gerações e não deve identificar o daemon.
5. GTK, cursores e ícones não eram instalados, embora os temas os referissem.
   Agora são baixados de revisão fixa via HTTPS, conferidos por SHA-256 e
   extraídos como dados em diretório privado; scripts dos arquivos não são executados.
6. Hyprpicker e checkupdates eram opcionais, apesar de haver botões padrão que
   os exigem. São obrigatórios. Fontes com nomes ausentes nos pacotes foram
   normalizadas para famílias instaladas; as diferenças estão em DEPENDENCIAS.md.
7. O wrapper rejeitava qualquer `DISPLAY`, inclusive possível resíduo do greeter.
   A entrada administrativa agora passa `--login`; a chamada TTY continua
   recusando execução dentro de uma sessão gráfica existente.
8. O guia de atalhos tinha SCSS copiado sem widget: foi integrado ao Eww
   com atalhos da adaptação e a paleta do tema; não abre mais um menu Rofi.
9. O erro final do bootstrap afirmava que nenhum arquivo havia sido aplicado,
   mesmo quando falhava depois da cópia. Agora informa instalação incompleta e
   preserva a indicação do backup.

A entrada `.desktop` já apontava ao wrapper e ele já passava `--config` ao
`start-hyprland`. O atalho de terminal já passava `--config current/kitty.conf`.
Esses caminhos foram preservados e receberam testes comportamentais.

## Hipóteses que precisam da VM

Não sabemos qual entrada de login foi selecionada, qual configuração/compositor
estava em execução, se os binários da VM aceitam todos os arquivos, ou se há
conflitos de processos, D-Bus, driver/DRM, escala ou aceleração da VM.
Selecionar a entrada genérica **Hyprland** continua carregando a configuração
normal daquele ambiente; ela não é removida nem substituída.

## Relatório mínimo

Depois de atualizar, rode dentro da sessão nova; se ela não abrir, rode no TTY:

```bash
~/.local/bin/gh0stzk diagnose > ~/gh0stzk-diagnostico.json
```

Envie somente esse JSON inicialmente. Ele inclui pacotes/comandos ausentes,
versões, sessão, argumentos de configuração dos componentes, geração, tema,
fontes, recursos visuais e categorias de erros. A configuração do compositor
é lida dos argumentos em `/proc` quando possível; o caminho esperado não é
apresentado como prova de que foi carregado.

Não despeja ambiente, títulos de janelas, clipboard, metadados de música nem
logs brutos. Os logs são resumidos em categorias e posições nas últimas 300
linhas. Se necessário, pediremos depois apenas o trecho específico, revisado
localmente. Não envie `env`, `systemctl --user show-environment` ou journal inteiro.

## Fluxo esperado

`instalar.sh` → `bootstrap.py` (pacotes, Eww, recursos externos, validação) →
`install.py` (backup, arquivos, entrada, geração inicial) → saída voluntária →
**Hyprland — gh0stzk** → `gh0stzk-session --login` → perfil privado →
`start-hyprland -- --config .../config/hyprland.lua` → `current/theme.lua` →
callback `gh0stzk session` → aparência, wallpaper, barras, Dunst, Eww, idle e
clipboard. Launcher e terminal abrem sob demanda com a configuração gerada.
