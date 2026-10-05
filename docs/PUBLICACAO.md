# Publicação deste repositório

Este projeto ainda **não** é um repositório Git: o diretório de trabalho não tem
`.git`, portanto `git remote -v` não retorna nada. Nada aqui cria, envia ou
torna público nada por você. O que falta é decidir o destino e rodar os
comandos abaixo.

## 1. Conferir o estado antes de publicar

```bash
cd /caminho/ate/este/diretorio
git rev-parse --is-inside-work-tree   # esperado: erro, ainda não é repositório
git remote -v                         # esperado: vazio
```

## 2. Onde a origem do instalador é definida

A origem e a referência ficam em **um único lugar**, no topo de `instalar.sh`:

```bash
PROJECT_REPO=''     # ← preencher com https://github.com/SEU_USUARIO/SEU_REPO
PROJECT_REF='main'
```

Enquanto `PROJECT_REPO` estiver vazio:

- dentro de uma cópia completa com remote `origin`, o instalador descobre a
  origem sozinha pelo remote (`git remote -v`);
- com **apenas** o `instalar.sh`, ele recusa e pede `--repo HTTPS_URL`.

`tools/validate.py` falha se `PROJECT_REPO` apontar para o upstream do gh0stzk.

## 3. Sequência de publicação

```bash
# repositório local
git init -b main
git add .
git commit -m "gh0stzk-hyprland: adaptação independente para Arch Linux e Hyprland 0.56+"

# remoto (ajuste o dono e o nome; gh CLI ou o navegador)
gh repo create SEU_USUARIO/SEU_REPO --public --source=. --remote=origin --push
# ou manualmente:
#   git remote add origin https://github.com/SEU_USUARIO/SEU_REPO.git
#   git push -u origin main
```

Depois preencha `PROJECT_REPO` no `instalar.sh`, rode a validação e faça um
segundo commit:

```bash
$EDITOR instalar.sh          # PROJECT_REPO='https://github.com/SEU_USUARIO/SEU_REPO'
python3 tools/validate.py --report docs/validation-static.json
python3 -m unittest discover -s tests -v
git add instalar.sh docs/validation-static.json
git commit -m "instalar.sh: origem centralizada no repositório publicado"
git push
```

Visibilidade, nome do repositório e dono são decisões suas. Nada acima altera
a visibilidade de nada que já exista.

## 4. O que já está pronto para publicação

- **Nenhum segredo.** Sem chaves, tokens, senhas ou `.env`. `tools/validate.py`
  falha se aparecer o caminho `/home/<usuário>` do autor em qualquer arquivo do
  projeto.
- **Sem caminhos pessoais.** Nenhum arquivo de configuração referencia sua home.
- **Sem logs, backups ou estado local.** `.gitignore` cobre `__pycache__/`,
  `*.log`, `*.tmp`, `backups/`, `.local/`, `.cache/`, `.venv/`, `.env*`,
  `*.pem`, `*.key`, `.agents/`, `.codex/`, `.aws/`.
- **`upstream/` não é publicado.** São 328 MB de referência de desenvolvimento e
  todo recurso necessário já está vendorizado e com hash em `resources.json`.
  A referência do commit original fica preservada em `UPSTREAM.json` e
  `CREDITS.md`.
- **Fontes sem licença de redistribuição individual ficam de fora.**
  `.gitignore` mantém só `assets/fonts/MapleMono-NF/`, que traz a licença
  própria. `install.py` aplica a mesma regra, então uma instalação nova nunca
  depende delas.
- **Recursos grandes.** `themes/` tem cerca de 51 MB (161 wallpapers + 18
  prévias) e `assets/` cerca de 15 MB. É o custo dos wallpapers originais e é
  intencional: sem eles a instalação teria que baixá-los de um repositório
  externo.
- **Permissões.** `instalar.sh`, `bin/gh0stzk` e `bin/gh0stzk-session` são
  executáveis; `tools/validate.py` falha se algum perder o bit.
- **Licença.** `LICENSE` é o GPL-3.0 do upstream, e o novo código é declarado
  GPL-3.0 em `CREDITS.md`.

Verifique o que realmente entraria no commit antes de enviar:

```bash
git status --short
git ls-files -s | awk '$1 != "100644" && $1 != "100755" {print}'
git count-objects -vH
```

## 5. Depois de publicar

```bash
curl -fLO https://raw.githubusercontent.com/SEU_USUARIO/SEU_REPO/main/instalar.sh
bash instalar.sh --dry-run     # deve mostrar a origem detectada e o plano completo
```

Se o `instalar.sh` avulso ainda reclamar de origem indefinida, o `PROJECT_REPO`
não foi preenchido ou publicado — corrija e faça novo push antes de divulgar o
link.

## 6. Melhorar a versão avulsa com uma tag

Enquanto `PROJECT_REF='main'`, o modo avulso resolve o branch e baixa **um**
commit por execução, sem misturar arquivos de revisões diferentes, e registra o
commit aplicado em `~/.local/state/gh0stzk-hyprland/backups/*/manifest.json`
(bloco `provenance`). Para fixar uma versão, publique uma tag e aponte para ela:

```bash
git tag -a v1.0.0 -m "gh0stzk-hyprland 1.0.0"
git push origin v1.0.0
$EDITOR instalar.sh     # PROJECT_REF='v1.0.0'
```

Com `--ref`, cada instalação escolhe a referência explicitamente e a
proveniência fica registrada.
