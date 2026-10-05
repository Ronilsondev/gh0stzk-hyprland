#!/usr/bin/env bash
# GPL-3.0. Adaptação independente gh0stzk -> Hyprland para Arch Linux.
# Este arquivo é o único bootstrap: instalar.sh decide o fluxo e delega a
# aplicação/restauração dos arquivos a install.py (via tools/bootstrap.py).
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

# ────────────────────────────────────────────────────────────────────────────
# FONTE ÚNICA DA ORIGEM — edite aqui ao publicar, ou passe --repo na chamada.
#   PROJECT_REPO : repositório GitHub desta ADAPTAÇÃO (não o upstream do gh0stzk)
#   PROJECT_REF  : branch, tag ou commit usado pelo modo avulso
# Se PROJECT_REPO ficar vazio, o instalador tenta descobrir pelo remote "origin"
# da cópia local completa (mesmo valor exibido por `git remote -v`).
# ────────────────────────────────────────────────────────────────────────────
PROJECT_REPO=''
PROJECT_REF='main'

UPSTREAM_REPO='https://github.com/gh0stzk/dotfiles'
MIN_FREE_KIB=2097152          # 2 GiB, além do espaço que o pacman calcula
REPO_PATTERN='^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$'

repo=$PROJECT_REPO ref=$PROJECT_REF dry=0 yes=0 origin_note='fixado no topo de instalar.sh'
options=()

usage() {
    cat <<'HELP'
Uso: bash instalar.sh [opções]

Instala esta adaptação dos dotfiles do gh0stzk em Arch Linux com Hyprland 0.56+.
Rode como usuário comum: o script usa sudo apenas nas operações administrativas
(pacman, systemctl do sistema e a entrada de sessão em /usr/share/wayland-sessions).

Opções:
  --dry-run             Mostra o plano inteiro sem alterar, baixar, atualizar ou
                        pedir senha. Funciona mesmo sem python3/git instalados.
  --yes                 Dispensa apenas a confirmação inicial. Não contorna a
                        autenticação do sudo nem as decisões do pacman/prompt.
  --repo HTTPS_URL      Repositório GitHub desta adaptação. Necessário no modo
                        avulso enquanto PROJECT_REPO estiver vazio. Nunca use o
                        upstream https://github.com/gh0stzk/dotfiles.
  --ref REF             Branch, tag ou commit (padrão: main). O modo avulso
                        baixa um único commit resolvido; nunca mistura revisões.
  --without-fonts       Não disponibiliza as fontes incluídas ao fontconfig.
  --without-portals     Preserva a preferência existente de xdg-desktop-portal.
  --without-session     Não registra a entrada "Hyprland - gh0stzk" no gerenciador
                        de login (nada é escrito em /usr/share/wayland-sessions).
  --optional PACOTE     Acrescenta um pacote de official_optional (repetível):
                        blueman, bluez, bluez-utils, hyprpicker, pacman-contrib,
                        uwsm, shellcheck.
  --with-eww ARQUIVO    Instala um pacote eww JÁ compilado por você como usuário
                        comum, via sudo pacman -U. Não usa helper AUR.
  --version             Mostra a identificação do instalador.
  --help                Mostra esta ajuda.

Exemplos:
  bash instalar.sh --dry-run
  bash instalar.sh
  bash instalar.sh --yes --optional hyprpicker --optional pacman-contrib
  bash instalar.sh --repo https://github.com/SEU_USUARIO/SEU_REPO --ref main

Fluxo real, nesta ordem:
  1. preflight: Arch Linux x86_64, usuário comum, espaço em disco, conectividade
  2. uma única confirmação: "Instalar e atualizar o sistema?" (--yes dispensa)
  3. bootstrap: git/python/curl por sudo pacman -Syu --needed, se faltarem
  4. origem: usa a cópia local completa, ou baixa UM commit fixo via HTTPS
  5. sudo pacman -Syu --needed <pacotes oficiais + opcionais selecionados>
  6. validação com os binários reais: Hyprland --verify-config, luac, Rofi,
     Waybar, Dunst
  7. install.py --apply: arquivos isolados + backup datado. Nada é sobrescrito
     sem backup; configurações de KDE, GNOME, BSPWM, Neovim e shell ficam intactas
  8. fc-cache, habilitação apenas de serviços inexistentes e resumo final

Atualização: usa sempre `pacman -Syu --needed`, que atualiza TODO o sistema e
depois instala. Não existe atualização parcial (`-Sy` seguido de instalação),
`--noconfirm` nunca é usado e `--allow-missing` nunca é usado. O fluxo não
reinicia nem encerra a sessão atual.

Aparência não é garantida: temas GTK, coleções de ícones e o cursor originais
ficam de fora (repositório de pacotes externo do autor, sem assinatura confiável).
O desktop funciona sem eles; veja docs/DEPENDENCIAS.md.
HELP
}

fail() { printf 'Erro: %s\n' "$*" >&2; exit 1; }
note() { printf '%s\n' "$*"; }

# Normaliza e valida a URL do repositório de destino desta adaptação.
validate_repo() {
    local candidate=${1%.git}
    candidate=${candidate/git@github.com:/https://github.com/}
    candidate=${candidate%.git}
    [[ $candidate =~ $REPO_PATTERN ]] ||
        fail "Use a URL HTTPS de um repositório do GitHub, sem credenciais: $1"
    [[ $candidate != "$UPSTREAM_REPO" ]] ||
        fail 'Esse é o upstream BSPWM do gh0stzk, não esta adaptação Hyprland.'
    printf '%s\n' "$candidate"
}

# Lê o remote "origin" da própria cópia local (mesmo valor de `git remote -v`).
discover_remote() {
    local dir=$1 url=
    command -v git >/dev/null 2>&1 || return 0
    git -C "$dir" rev-parse --is-inside-work-tree >/dev/null 2>&1 || return 0
    url=$(git -C "$dir" remote get-url origin 2>/dev/null) || return 0
    [[ -n $url ]] || return 0
    printf '%s\n' "$url"
}

# Leitura offline da versão desta cópia; não usa rede e não escreve nada.
local_commit() {
    command -v git >/dev/null 2>&1 || return 0
    git -C "$1" rev-parse --verify HEAD 2>/dev/null || return 0
}

while (($#)); do
    case "$1" in
        --help|-h) usage; exit 0 ;;
        --dry-run) dry=1 ;;
        --yes|-y) yes=1 ;;
        --repo|--ref|--optional|--with-eww)
            (($# >= 2)) && [[ -n $2 && $2 != --* ]] || fail "Falta valor para $1"
            case "$1" in
                --repo) repo=$2 ;;
                --ref) ref=$2 ;;
                *) options+=("$1" "$2") ;;
            esac
            shift ;;
        --without-fonts|--without-portals|--without-session) options+=("$1") ;;
        --version) note 'gh0stzk-hyprland (adaptação independente, GPL-3.0)'; exit 0 ;;
        *) fail "Opção desconhecida: $1 (veja --help)" ;;
    esac
    shift
done

[[ $ref != -* && $ref != *[[:space:]]* && -n $ref ]] || fail 'Referência inválida.'

root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
local_copy=0
[[ -f $root/install.py && -f $root/packages.json && -f $root/tools/bootstrap.py \
   && -f $root/config/hyprland.lua && -f $root/resources.json ]] && local_copy=1

# ── Origem e referência: único ponto de decisão ─────────────────────────────
if [[ -n $repo ]]; then
    repo=$(validate_repo "$repo")
    origin_note='informada por --repo'
elif ((local_copy)); then
    detected=$(discover_remote "$root")
    if [[ -n $detected ]]; then
        repo=$(validate_repo "$detected")
        origin_note="remote origin detectado: $detected"
    else
        origin_note='cópia local sem remote origin; proveniência registrada como local'
    fi
else
    origin_note='arquivo avulso; origem não definida'
fi

commit_here=$(local_commit "$root")
summary() {
    note ''
    note '── Resumo ──────────────────────────────────────────────────────────────'
    note 'Alvo                  : Arch Linux x86_64, Hyprland 0.56 ou posterior'
    note "Origem                : ${repo:-cópia local (sem repositório de origem)}"
    note "Referência            : $ref"
    note "Proveniência          : $origin_note"
    note "Commit desta cópia    : ${commit_here:-indisponível (cópia sem git)}"
    note 'Pacotes oficiais     : hyprland, waybar, rofi, dunst, swaybg, hyprlock,'
    note '                        hypridle, kitty, thunar, firefox, pavucontrol,'
    note '                        grim, slurp, wl-clipboard, cliphist, pipewire,'
    note '                        wireplumber, portais, networkmanager, fontes, ícones'
    note 'Atualiza o sistema?   : SIM - pacman -Syu --needed (atualização total)'
    note 'Sessão atual          : não será reiniciada nem encerrada'
    note 'Gerenciador de login  : não será substituído; apenas uma entrada nova'
    note 'Backup antes de sobrescrever: ~/.local/state/gh0stzk-hyprland/backups'
    note 'Ainda opcionais       : Eww (AUR), temas GTK, cursor e ícones do autor'
    note '──────────────────────────────────────────────────────────────────────────'
}

note 'gh0stzk -> Hyprland: instalador único para Arch Linux x86_64.'
note "Origem: ${repo:-cópia local; repositório de origem ainda não definido}"
note "Referência: $ref ($origin_note)"
note ''
note 'ATENÇÃO: este fluxo atualizará TODO o sistema com pacman -Syu --needed.'
note 'Depois instala o desktop, valida a configuração com os binários reais e'
note 'aplica os arquivos com backup datado. Não usa --noconfirm, não usa AUR, não'
note 'substitui o gerenciador de login e não encerra a sua sessão.'
summary

if ((dry)); then
    note ''
    note 'DRY-RUN: nada será baixado, instalado, atualizado, habilitado ou escrito.'
    note 'Nenhuma senha será pedida.'
    if ((local_copy)) && command -v python3 >/dev/null 2>&1; then
        note 'Cópia local completa detectada: conferindo manifesto, recursos e plano de arquivos.'
        python3 -B "$root/tools/bootstrap.py" --dry-run \
            --source "${repo:-local}" --ref "$ref" "${options[@]}" ||
            fail 'Plano recusado na inspeção. Nada foi alterado; leia o erro acima.'
    else
        note ''
        note 'LIMITAÇÃO DESTE DRY-RUN:'
        note '  - você está com apenas o instalar.sh, ou sem python3 disponível;'
        note '  - por isso não dá para ler packages.json, conferir os 18 temas, os'
        note '    hashes de resources.json ou listar os arquivos a alterar sem obter o'
        note '    restante do projeto, e obter exigiria rede e escrita em disco, que um'
        note '    dry-run não faz;'
        note '  - nada foi inventado: o plano real só pode ser exibido após o download;'
        note '    para vê-lo agora, use uma cópia completa do repositório:'
        note '      git clone <origem> && cd REPOSITORIO && bash instalar.sh --dry-run'
        note '  - o fluxo real será: preflight (Arch, usuário, espaço, rede) ->'
        note '    sudo pacman -Syu --needed do bootstrap -> fetch HTTPS da referência ->'
        note '    checkout de UM commit -> validação de manifesto e recursos ->'
        note '    sudo pacman -Syu --needed dos pacotes -> Hyprland --verify-config ->'
        note '    install.py --apply -> fc-cache.'
        note '  - nenhuma etapa será pulada no modo real.'
    fi
    exit 0
fi

((local_copy)) || [[ -n $repo ]] || fail \
    'Origem ainda não definida. Informe --repo https://github.com/SEU_USUARIO/SEU_REPO
   ou preencha PROJECT_REPO no topo de instalar.sh antes de publicar.'

# ── Preflight: sem escrita e sem sudo ────────────────────────────────────────
[[ $(id -u) != 0 ]] || fail 'Execute como usuário comum. Não use sudo bash instalar.sh.'
# /etc/os-release pertence ao sistema operacional, não ao projeto baixado.
# shellcheck disable=SC1091
source /etc/os-release
[[ ${ID:-} == arch ]] || fail "Alvo exclusivo: Arch Linux (ID=arch), encontrado ID=${ID:-desconhecido}."
[[ $(uname -m) == x86_64 ]] || fail "Arquitetura suportada: x86_64 (encontrada $(uname -m))."
for command in sudo pacman df awk mktemp; do
    command -v "$command" >/dev/null || fail "Pré-requisito do Arch ausente: $command"
done
for path in / "$HOME" "${TMPDIR:-/tmp}"; do
    free=$(df -Pk -- "$path" | awk 'END {print $4}')
    if [[ ! $free =~ ^[0-9]+$ ]] || ((free < MIN_FREE_KIB)); then
        fail "Menos de 2 GiB disponíveis em $path. O pacman precisa de espaço adicional para a atualização."
    fi
done

# Conectividade: apenas leitura. Sem curl, o próprio pacman falhará mais adiante.
if command -v curl >/dev/null 2>&1; then
    curl --fail --silent --show-error --location --proto '=https' --proto-redir '=https' \
        --connect-timeout 15 --max-time 45 --output /dev/null 'https://archlinux.org/' ||
        fail 'Sem conectividade HTTPS com archlinux.org.'
    if ((!local_copy)); then
        curl --fail --silent --show-error --location --proto '=https' --proto-redir '=https' \
            --connect-timeout 15 --max-time 45 --output /dev/null 'https://github.com/' ||
            fail 'Sem conectividade HTTPS com github.com, necessária para baixar o projeto.'
    fi
    note 'Conectividade HTTPS verificada com archlinux.org.'
    ((local_copy)) || note 'Conectividade HTTPS verificada com github.com.'
else
    note 'curl ausente: a conectividade será verificada pelo próprio pacman durante a instalação.'
fi

if ((!yes)); then
    read -r -p 'Instalar e atualizar o sistema agora? [s/N] ' answer || fail 'Confirmação não recebida.'
    [[ $answer == s || $answer == S ]] || { note 'Cancelado. Nada foi alterado.'; exit 0; }
fi

# ── Bootstrap das ferramentas mínimas do próprio instalador ─────────────────
missing=()
for pair in python3:python git:git curl:curl; do
    command -v "${pair%%:*}" >/dev/null || missing+=("${pair#*:}")
done
if ((${#missing[@]})); then
    note "Bootstrap: instalando ${missing[*]} com atualização total antes de prosseguir."
    sudo pacman -Syu --needed -- "${missing[@]}" ||
        fail 'Falha no bootstrap de dependências; confira rede, mirrors e sudo.'
fi

# ── Origem do projeto ────────────────────────────────────────────────────────
tmp=''
cleanup() { if [[ -n $tmp && -d $tmp ]]; then rm -rf -- "$tmp"; fi; }
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

if ((local_copy)); then
    note "Usando a cópia local completa em $root"
else
    tmp=$(mktemp -d "${TMPDIR:-/tmp}/gh0stzk-download.XXXXXXXX")
    note "Baixando $repo @ $ref por HTTPS, em um único commit, para $tmp"
    git -C "$tmp" init -q
    # hooks desativados e protocolo file bloqueado: o repositório remoto não tem
    # nada executado durante o download.
    git -C "$tmp" -c protocol.file.allow=never -c core.hooksPath=/dev/null \
        fetch --depth=1 -- "$repo" "$ref" ||
        fail 'Download do Git falhou (URL, referência ou conexão). Dotfiles NÃO foram aplicados.'
    commit=$(git -C "$tmp" rev-parse --verify 'FETCH_HEAD^{commit}') ||
        fail 'Não foi possível resolver um único commit para a referência. Dotfiles NÃO foram aplicados.'
    git -C "$tmp" -c core.hooksPath=/dev/null checkout --detach "$commit" ||
        fail 'Checkout incompleto. Dotfiles NÃO foram aplicados.'
    root=$tmp
    commit_here=$commit
    note "Commit obtido: $commit"
fi

for needed in tools/bootstrap.py install.py packages.json resources.json config/hyprland.lua; do
    [[ -f $root/$needed ]] || fail "Projeto obtido incompleto: falta $needed. Nada foi aplicado."
done

python3 -B "$root/tools/bootstrap.py" \
    --source "${repo:-local}" --ref "$ref" "${options[@]}" ||
    fail 'tools/bootstrap.py falhou. Nenhuma configuração foi aplicada; leia a etapa acima.'
