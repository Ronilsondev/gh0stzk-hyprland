# Evidências e limites desta correção

Testes antigos de presença de strings não são prova de funcionamento gráfico.
O relato da VM motivou o rastreamento documentado em [DIAGNOSTICO.md](DIAGNOSTICO.md).

| Nível | Executado aqui | O que falta na VM |
|---|---|---|
| Pacotes instalados | Nenhum pacote foi instalado na máquina principal; transações simuladas nos testes | pacman real, build de Eww e dependências |
| Arquivos aplicados | Cópia real em homes temporárias, backups/restauração, geração de Emilia e demais temas | instalação na home da VM |
| Recursos externos | Download real dos 15 arquivos, hashes/metadados GPL3, extração isolada, conferência dos 18 GTKs, ícones, cursores e heranças | resolução de recursos pelos programas da VM |
| Sessão disponibilizada | `.desktop`/journal em diretório temporário; wrapper executado com compositor simulado | seleção real no login, TTY e inicialização do compositor |
| Configuração aceita | Sintaxe Lua com luac; callback executado pelo Lua real; configuração gerada conferida estruturalmente | Hyprland, Rofi, Waybar, Dunst, Eww, Kitty, Hyprlock/Hypridle reais |
| Desktop/aparência | **Nenhuma sessão gráfica aberta; nenhuma captura da migração** | Emilia primeiro; depois os demais 17, múltiplos painéis/vertical/escala |

## Regressões comportamentais

A suíte preserva os 36 testes anteriores e acrescenta testes em
`tests/test_session_flow.py`:

- Executa o callback de `hyprland.start` em Lua, e seu comando no shell: o
  controlador recebe exatamente `session`, inclusive com caminho com espaços.
- Instala em home temporária e executa o wrapper com binários simulados;
  verifica o argv final, tema persistido, perfil privado e tratamento do greeter.
- Confere que o terminal recebe o arquivo Kitty da geração.
- Exerce o isolamento GTK/GSettings, preservando preferências de aplicativos.
- Gera Emilia primeiro e os outros temas, verifica recursos consumidos, seis
  painéis de Pamela e a orientação vertical de Z0mbi3.
- Verifica que falta/falha do Eww propaga erro, sem fallback para menus.
- Recusa aplicar GSettings globais e publicar recursos incompletos.
- Exercita rollback após rejeição nativa simulada e início idempotente de um
  processo real de teste (`sleep`) em registro temporário, com encerramento.
- Atualiza instalação temporária mantendo o tema escolhido e as preferências.

Os mocks não são considerados aceitação pelos programas reais. O relatório
`tools/validate.py` mantém `graphical_session_tested: false` e marca binários
nativos ausentes; Rofi também é marcado como não executado se faltar display.

## Recursos originais incompletos

No ensaio dos arquivos fixados foram encontrados **67 links externos omitidos
e 203 links quebrados**. São 194 ocorrências em Glassy, 41 em Hack, 28 em
Zafiro, seis em Vimix-White e uma em Candy. A lista exata, sem dados pessoais,
está em [visual-limitations.json](visual-limitations.json). O instalador gera
seu próprio relatório e não oculta esses limites.

A composição dos widgets foi adaptada para Wayland; Andrea/Z0mbi3 usam barras
Waybar e widgets Eww. Não há alegação de identidade pixel a pixel com o BSPWM.
Fontes/licenças e GTK 4 estão descritos em [DEPENDENCIAS.md](DEPENDENCIAS.md).

## Reproduzir sem instalar

```bash
bash -n instalar.sh
python3 -m unittest discover -s tests -v
python3 tools/validate.py --report /tmp/gh0stzk-validacao.json
python3 tools/resource_manifest.py --check
python3 install.py --dry-run
bash instalar.sh --dry-run
```

A receita de Eww foi conferida contra o fonte v0.6.0 e fixada por SHA-256;
**a compilação não foi executada aqui**. ShellCheck não está disponível neste
ambiente; `bash -n` foi executado. O histórico anterior de ShellCheck não é
apresentado como validação desta revisão.

## Conferência para publicação (2026-10-07)

Os 50 testes passaram, incluindo três testes do `resource_manifest --check`
(sucesso, divergência/manifesto inválido sem escrita e exclusão de fontes sem
licença). A suíte em Python 3.14 emitiu um `ResourceWarning` no teste de processo
`sleep`; o teste passou, mas o aviso de ciclo de vida de `Popen` não é uma
validação gráfica. Sintaxe Bash, validador dos 18 temas, 276 hashes de recursos
e os dry-runs de `install.py`, instalador local e instalador avulso passaram.
O relatório [validation-static.json](validation-static.json) coincide com a
execução desta preparação e mantém `graphical_session_tested: false`.
Nenhum pacote foi instalado neste computador e nenhuma sessão gráfica iniciada.

O roteiro gráfico e o relatório mínimo da VM estão em [SESSAO.md](SESSAO.md).
