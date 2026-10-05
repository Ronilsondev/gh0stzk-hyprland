# Resultados da validação

Registro automatizado no relatório JSON vizinho, produzido por
`python3 tools/validate.py --report docs/validation-static.json`.

## Passou

- Sintaxe de Python e Lua (`luac -p`).
- `bash -n` no `instalar.sh` e **ShellCheck 0.11.0 sem avisos**.
- `instalar.sh` tem os itens obrigatórios: `PROJECT_REPO`/`PROJECT_REF`,
  `--dry-run`, `--yes`, `--help`, `pacman -Syu --needed`, `git init` e
  `FETCH_HEAD^{commit}`. O validador falha se a origem apontar para o upstream.
- Bit de execução em `instalar.sh`, `bin/gh0stzk` e `bin/gh0stzk-session`.
- Estrutura JSON dos 18 temas, preferências e pacotes.
- Geração estática de configurações para os 18 temas, todos os painéis e duas
  saídas simuladas (uma com escala e rotação).
- Módulos Waybar referenciados existem; os 18 temas incluem barras Wayland.
- Formato INI do Dunst e `force_xwayland=false`.
- Delimitadores, imports, CSS, assets locais, tokens de template.
- Nenhum caminho pessoal (nenhum `/home/<usuário>` do autor) e nenhum comando
  BSPWM/X11 em arquivo executável, incluindo os arquivos da raiz.
- Commit, conjunto de 18 temas, hashes de 161 wallpapers e 18 prévias conferidos
  contra o upstream sem alterações.
- `packages.json` validado: categorias sem sobreposição, nomes válidos, e origem
  declarada para cada item de AUR e de recurso externo.
- Instalador completo aplicado numa home temporária com espaços no caminho,
  com fontes, portais, executáveis e links. Dry-run não escreve nada.
- Segunda aplicação idempotente; backup datado; preferências locais
  pré-existentes preservadas; pai symlink recusado.
- Restauração real protege arquivo editado depois da instalação e arquivo
  adicional, restaura o symlink original e deixa `local.lua` do usuário intacto.
- Entrada de sessão: gravação, permissões, journal administrativo, restauração
  idempotente e preservação de edição posterior.
- Download avulso com um único commit resolvido; falha de download e de checkout
  sem tocar na home; temporários do próprio instalador removidos.
- Falha do `pacman` e configuração recusada pelo Hyprland param **antes** de
  qualquer arquivo ser aplicado; `--allow-missing` e `--noconfirm` nunca usados.
- Persistência offline, rollback exato do diretório anterior, tema inexistente,
  falha na validação antes da troca, falha de serviço em troca simulada,
  confirmação de energia em modo cancelar e não reutilização indevida de PID.

O conjunto completo é executado com:

```bash
python3 -m unittest discover -s tests -v
python3 tools/validate.py --report docs/validation-static.json
bash instalar.sh --dry-run
python3 install.py
```

## `luac` não é Hyprland

`luac -p` confirma apenas que `config/*.lua` é Lua válido. A compatibilidade
com o Hyprland é responsabilidade do parser do próprio compositor, executado
por `Hyprland --verify-config`. São coisas diferentes e o relatório JSON
declara as duas separadamente (`static` e `hyprland_version`, mais o bloco
`caveats`).

## Não executado neste ambiente

- **Nenhuma sessão gráfica.** Hyprland, Waybar, Rofi, Dunst, Eww, Hyprlock e
  Hypridle não estão instalados aqui. `Hyprland --verify-config` está
  implementado e roda automaticamente quando o binário existe; aqui não existe,
  então o relatório marca `hyprland_version: ausente`.
- **Parsers nativos** de Waybar, Rofi, Dunst, Eww, Hyprlock e Hypridle. O
  verificador estruturado confere delimitadores, imports e referências, o que
  **não** substitui esses programas.
- **`shellcheck` instalado.** O `instalar.sh` foi analisado com o binário
  0.11.0 baixado para `/tmp`, sem instalar nada no sistema. `validate.py` usa
  `shellcheck` automaticamente quando ele está disponível.
- **Nenhum `pacman`, `sudo`, serviço ou download real.** Todos os testes
  administrativos usam comandos simulados e diretórios temporários.

Não houve captura de tela comparativa. A prévia no repositório é do original
BSPWM e não é screenshot da migração. Todos os temas ficam como
**estático passou; gráfico pendente**, sem declaração de funcionamento visual ou
funcional antes do ensaio em Arch descrito em [SESSAO.md](SESSAO.md).

Uma configuração renderizada ainda pode ser recusada pela compilação real das
dependências, por fonte ausente, por recurso do driver, por limitação de
resolução ou por preferências locais do usuário. O resultado estático não valida
comportamento em VM nem garante um desktop funcional antes desse ensaio.
