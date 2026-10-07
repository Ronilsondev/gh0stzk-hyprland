# Publicação deste repositório

Este projeto **já está publicado** em
<https://github.com/Ronilsondev/gh0stzk-hyprland>, com visibilidade pública. O
remote `origin` local aponta para lá e a origem do instalador está fixada no
mesmo lugar, então ninguém precisa editar nada para instalar.

```bash
git remote -v            # origin  git@github.com:Ronilsondev/gh0stzk-hyprland.git
git log --oneline -1     # commit publicado
```

## 1. Onde a origem do instalador é definida

A origem e a referência ficam em **um único lugar**, no topo de `instalar.sh`:

```bash
PROJECT_REPO='https://github.com/Ronilsondev/gh0stzk-hyprland'
PROJECT_REF='main'
```

O modo avulso (`curl` + `instalar.sh`) baixa `PROJECT_REF` e registra o commit
aplicado em `~/.local/state/gh0stzk-hyprland/backups/*/manifest.json`. Dentro de
uma cópia clonada com remote `origin`, a descoberta por `git remote -v` ocorre
somente se `PROJECT_REPO` estiver vazio; `--repo` sempre tem prioridade.
Para reproduzir uma entrega, baixe o instalador pelo SHA completo publicado e
passe esse mesmo SHA em `--ref`, conforme o [README](../README.md).

`tools/validate.py` falha se:

- `PROJECT_REPO` apontar para o upstream `https://github.com/gh0stzk/dotfiles`;
- `PROJECT_REPO` não for uma URL HTTPS do GitHub;
- `PROJECT_REPO` for diferente do remote `origin` do próprio projeto.

Um teste automatizado (`test_published_origin_matches_remote`) confere o mesmo
ponto, então trocar a constante sem trocar o remote quebra a validação.

## 2. Se você fizer um fork

```bash
git clone https://github.com/Ronilsondev/gh0stzk-hyprland
cd gh0stzk-hyprland
git remote rename origin upstream
git remote add origin https://github.com/SEU_USUARIO/SEU_REPO.git
$EDITOR instalar.sh        # PROJECT_REPO='https://github.com/SEU_USUARIO/SEU_REPO'
python3 tools/validate.py --report docs/validation-static.json
python3 -m unittest discover -s tests -v
git commit -am "instalar.sh: origem centralizada no meu fork"
git push -u origin main
```

Depois de publicar, confira o caminho de instalação real:

```bash
curl -fLO https://raw.githubusercontent.com/SEU_USUARIO/SEU_REPO/main/instalar.sh
bash instalar.sh --dry-run     # mostra origem fixada e limitações do modo avulso
```

Se o `instalar.sh` avulso reclamar de origem indefinida, o `PROJECT_REPO` não foi
preenchido ou publicado — corrija e faça novo push antes de divulgar o link.

## 3. O que foi conferido antes de publicar

- **Nenhum segredo.** Sem chaves, tokens, senhas ou `.env`. `tools/validate.py`
  falha se aparecer o caminho `/home/<usuário>` do autor em qualquer arquivo
  executável.
- **Sem caminhos pessoais.** Nenhum arquivo de configuração referencia sua home.
- **Sem logs, backups ou estado local.** `.gitignore` cobre `__pycache__/`,
  `*.log`, `*.tmp`, `backups/`, `.local/`, `.cache/`, `.venv/`, `.env*`,
  `*.pem`, `*.key`, `.agents/`, `.claude/`, `.codex/`, `.aws/`.
- **`upstream/` não foi publicado.** São 328 MB de referência de desenvolvimento e
  todo recurso necessário já está vendorizado e com hash em `resources.json`.
  A referência do commit original fica preservada em `UPSTREAM.json` e
  `CREDITS.md`.
- **Fontes sem licença de redistribuição individual ficaram de fora.**
  `.gitignore` mantém só `assets/fonts/MapleMono-NF/`, que traz a licença
  própria. `install.py` aplica a mesma regra, então uma instalação nova nunca
  depende delas.
- **Recursos grandes.** `themes/` tem cerca de 51 MB (161 wallpapers + 18
  prévias) e `assets/` cerca de 15 MB. É o custo dos wallpapers originais e é
  intencional: sem eles a instalação teria que baixá-los de um repositório
  externo. GitHub aceita o tamanho; nenhum arquivo passa de 2,1 MB.
- **Permissões.** `instalar.sh`, `bin/gh0stzk` e `bin/gh0stzk-session` são
  executáveis; `tools/validate.py` falha se algum perder o bit.
- **Licença.** `LICENSE` é o GPL-3.0 do upstream, e o novo código é declarado
  GPL-3.0 em `CREDITS.md`.

Verifique o que realmente entrou no commit a qualquer momento:

```bash
git status --short
git ls-files -s | awk '$1 != "100644" && $1 != "100755" {print}'
git count-objects -vH
```

## 4. Fixar uma versão com tag

Enquanto `PROJECT_REF='main'`, o modo avulso resolve o branch e baixa **um**
commit por execução, sem misturar arquivos de revisões diferentes, e registra o
commit aplicado em `~/.local/state/gh0stzk-hyprland/backups/*/manifest.json`
(bloco `provenance`). Para fixar uma versão, publique uma tag e aponte para ela:

```bash
git tag -a v1.0.0 -m "gh0stzk-hyprland 1.0.0"
git push origin v1.0.0
$EDITOR instalar.sh     # PROJECT_REF='v1.0.0'
```

Usuários que preferirem a branch podem passar `--ref main`. Com `--ref`, cada
instalação escolhe a referência explicitamente e a proveniência continua
registrada.