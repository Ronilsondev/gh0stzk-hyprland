# gh0stzk · adaptação independente para Hyprland

Migração dos dotfiles de [gh0stzk](https://github.com/gh0stzk/dotfiles), commit
`bbcd8b00e537ddad63d34a0c448e5bd539078fcb`, para **Arch Linux / Hyprland 0.56+**.
Não é um lançamento oficial do autor original. Licença GPL-3.0, créditos em
[CREDITS.md](CREDITS.md). A referência do commit original fica em
[UPSTREAM.json](UPSTREAM.json).

**Estado: pronto para instalar, validação gráfica ainda pendente.** Nenhuma sessão
Hyprland foi aberta até aqui. Leia [VALIDACAO.md](docs/VALIDACAO.md) antes de
instalar e [SESSAO.md](docs/SESSAO.md) para o ensaio em VM.

## Instalação em três passos

Baixe **apenas** o `instalar.sh` e execute. Ele baixa o restante do projeto,
confere tudo, instala as dependências e aplica os dotfiles com backup.

```bash
curl -fLO https://raw.githubusercontent.com/SEU_USUARIO/SEU_REPO/main/instalar.sh
bash instalar.sh
```

> Troque `SEU_USUARIO/SEU_REPO` pelo repositório donde você baixou o arquivo. É
> essa URL que o próprio `instalar.sh` passa a usar para obter o projeto.

O instalador mostra um resumo, pede **uma única confirmação** e só então pede a
senha do `sudo` para as operações administrativas. Ele **atualiza todo o
sistema** com `pacman -Syu --needed` antes de instalar — não existe atualização
parcial. Nada da sua sessão é reiniciado ou encerrado.

Se preferir clonar (também funciona):

```bash
git clone https://github.com/SEU_USUARIO/SEU_REPO
cd SEU_REPO && bash instalar.sh
```

## Opções

```bash
bash instalar.sh --help          # todas as opções e exemplos
bash instalar.sh --dry-run       # mostra o plano sem baixar, instalar nem pedir senha
```

| Opção | Efeito |
|---|---|
| `--dry-run` | Plano completo sem alterar, baixar, atualizar ou pedir senha. Funciona mesmo sem `python3`/`git`. |
| `--yes` | Dispensa só a confirmação inicial. Não contorna o `sudo` nem as decisões do `pacman`. |
| `--repo HTTPS_URL` | Repositório desta adaptação (nunca o upstream do gh0stzk). |
| `--ref REF` | Branch, tag ou commit. O modo avulso baixa **um** commit resolvido. |
| `--optional PACOTE` | Acrescenta um opcional oficial: `blueman`, `bluez`, `bluez-utils`, `hyprpicker`, `pacman-contrib`, `uwsm`, `shellcheck`. Repetível. |
| `--with-eww ARQUIVO` | Instala um pacote `eww` **já compilado por você**, via `sudo pacman -U`. |
| `--without-fonts` | Não disponibiliza as fontes incluídas ao fontconfig. |
| `--without-portals` | Preserva a preferência existente de `xdg-desktop-portal`. |
| `--without-session` | Não registra a entrada de sessão no gerenciador de login. |

## O que é instalado

**Oficiais obrigatórios** — `hyprland`, `waybar`, `rofi`, `dunst`, `swaybg`,
`hyprlock`, `hypridle`, `kitty`, `thunar`, `firefox`, `pavucontrol`, `grim`,
`slurp`, `wl-clipboard`, `cliphist`, `brightnessctl`, `playerctl`, `pipewire`,
`pipewire-pulse`, `wireplumber`, `xdg-desktop-portal`,
`xdg-desktop-portal-hyprland`, `xdg-desktop-portal-gtk`, `hyprpolkitagent`,
`networkmanager`, `libnotify`, `python`, `lua`, `procps-ng`,
`ttf-jetbrains-mono-nerd`, `ttf-inconsolata`, `ttf-terminus-nerd`,
`papirus-icon-theme`, `webp-pixbuf-loader`, `git`, `curl`, `fontconfig`, `dbus`,
`mesa`, `xdg-utils`, `adwaita-icon-theme`, `adwaita-cursors`.

**Oficiais opcionais** — `blueman`, `bluez`, `bluez-utils`, `hyprpicker`,
`pacman-contrib`, `uwsm`, `shellcheck`.

**AUR** — apenas `eww`, e somente se você compilar o pacote e passá-lo com
`--with-eww`. Nenhum helper AUR (`paru`, `yay`) é instalado e nada é compilado
como root.

Recursos do autor fora deste repositório — temas GTK, o cursor `Qogirr` e as
coleções de ícones `gh0stzk-icons-*` — são publicados por ele em
`http://gh0stzk.github.io/pkgs/x86_64` com `SigLevel = Optional TrustAll`, ou
seja, **sem chave de assinatura auditável**. Por isso esta adaptação **não
adiciona esse repositório** e usa `papirus-icon-theme` + `adwaita-cursors` como
alternativas oficiais. Os nomes originais continuam nos temas, para você
instalar de fonte auditada se quiser. A lista completa, com a origem de cada um,
está em [DEPENDENCIAS.md](docs/DEPENDENCIAS.md) e em `packages.json`.

**Aparência não é idêntica à do autor** enquanto esses recursos não forem
instalados por você. Todo o resto — 18 temas, wallpapers, barras Waybar, Rofi,
Dunst, Hyprlock, Hypridle, fontes, portais e entrada de sessão — funciona com
pacotes oficiais.

## Iniciar a sessão

A instalação registra uma entrada **Hyprland — gh0stzk** em
`/usr/share/wayland-sessions`, usando o wrapper do projeto. Saia da sua sessão
**voluntariamente** e escolha essa entrada. Nada é desligado por você.

```bash
# Alternativa por TTY, sem passar pelo gerenciador de login:
~/.local/bin/gh0stzk-session
```

O wrapper exige Hyprland 0.56+ e falha de forma explícita se você o chamar
dentro de outra sessão gráfica. O gerenciador de login instalado não é
substituído, e a entrada nova tem arquivo administrativo registrado em
`/var/lib/gh0stzk-hyprland/sessions`, então a restauração a remove.

Atalhos principais: `Super+Enter` terminal, `Super+Espaço` aplicativos,
`Alt+Espaço` temas, `Super+Alt+W` wallpapers, `Alt+F1` guia,
`Super+Alt+P` energia, `Super+Ctrl+L` bloqueio.
[Todos os atalhos](docs/ATALHOS.md).

```bash
~/.local/bin/gh0stzk list              # temas e estado
~/.local/bin/gh0stzk theme emilia      # troca de tema
~/.local/bin/gh0stzk refresh           # reaplica e lê os monitores
~/.local/bin/gh0stzk rollback          # volta à geração anterior
```

Trocar tema prepara uma geração, valida os arquivos, troca um link atômico,
recarrega o Hyprland e reinicia só os processos registrados por esta adaptação.
Falhas detectadas recuperam a geração anterior. Isso não é uma transação
gráfica: pode haver um breve intervalo sem barra. Registros em
`~/.local/state/gh0stzk-hyprland/*.log`.

## Personalizar

Edite `~/.config/gh0stzk-hyprland/local.lua` para teclado, escala, monitores e
atalhos, e `preferences.json` para aplicativos, widgets e wallpapers.
`Super+R` abre o editor de aparência por tema. Detalhes em
[USO.md](docs/USO.md).

A instalação **só cria** `local.lua` e `preferences.json` se não existirem; se
você já os tiver, são preservados. O mesmo vale para a sua preferência de
portais. Configurações de KDE, GNOME, BSPWM, Neovim, shell, Kitty global e
Firefox global **não são tocadas**, e nenhum ambiente gráfico é removido.

## Atualizar

Rode o instalador de novo. Ele reaplica só o que mudou e faz backup antes:

```bash
bash instalar.sh            # dentro do repositório, ou o mesmo comando do passo 1
```

Instalação e atualização são repetíveis; a segunda execução normalmente não
altera nada.

## Restaurar

O instalador informa o diretório do backup na aplicação. Copie **exatamente**
esse caminho:

```bash
python3 ~/.local/share/gh0stzk-hyprland/install.py --restore CAMINHO_DO_BACKUP
python3 ~/.local/share/gh0stzk-hyprland/install.py --restore CAMINHO_DO_BACKUP --apply
```

A primeira chamada só inspeciona. A segunda restaura **apenas** arquivos que
continuam idênticos aos que o instalador escreveu: alterações suas ficam
preservadas e a chamada sai com código 2. Não remove pacotes, diretórios
inteiros, gerações de tema nem arquivos criados depois. Restaure **fora** de uma
sessão Hyprland, e vários backups do mais recente para o mais antigo.

A restauração devolve arquivos. Pacotes instalados, a atualização do sistema e
os serviços que foram habilitados **não** são revertidos.

Ensaio totalmente isolado, sem tocar na sua conta:

```bash
teste=$(mktemp -d)
python3 install.py --home "$teste"
python3 install.py --home "$teste" --apply --allow-missing
backup=$(find "$teste/.local/state/gh0stzk-hyprland/backups" -mindepth 1 -maxdepth 1 -type d | sort | tail -n 1)
python3 install.py --home "$teste" --restore "$backup" --apply
```

## Verificar sem instalar

```bash
bash instalar.sh --dry-run   # plano completo, offline quando é possível
python3 tools/validate.py    # gera e valida as configurações dos 18 temas
python3 install.py           # dry-run do aplicador de arquivos
python3 -m unittest discover -s tests -v
```

`--allow-missing` só prepara arquivos e **não** declara um desktop funcional; o
fluxo normal nunca o usa.

## Documentação

· [DEPENDENCIAS.md](docs/DEPENDENCIAS.md) — pacotes, versões e o que continua
opcional
· [VALIDACAO.md](docs/VALIDACAO.md) — o que foi verificado e o que não foi
· [SESSAO.md](docs/SESSAO.md) — ensaio em VM Arch e sessão real
· [TEMAS.md](docs/TEMAS.md) — os 18 temas e a composição preservada
· [MIGRACAO.md](docs/MIGRACAO.md) — o que mudou em relação ao BSPWM original
· [USO.md](docs/USO.md) — personalização e recuperação
· [ATALHOS.md](docs/ATALHOS.md) — tabela de atalhos
· [FONTES.md](docs/FONTES.md) — documentação oficial consultada
· [PUBLICACAO.md](docs/PUBLICACAO.md) — como publicar este repositório
