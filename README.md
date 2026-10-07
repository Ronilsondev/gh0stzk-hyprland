# gh0stzk · adaptação independente para Hyprland

Adaptação dos [dotfiles de gh0stzk](https://github.com/gh0stzk/dotfiles), commit
`bbcd8b00e537ddad63d34a0c448e5bd539078fcb`, para Arch Linux / Hyprland 0.56+.
GPL-3.0; não é um lançamento oficial do autor. Veja [CREDITS.md](CREDITS.md).

**Fluxo de instalação corrigido; validação gráfica na VM ainda pendente.**
Os testes automatizados não provam que a aparência foi reproduzida. O autostart
anterior chamava `gh0stzksession`, um executável inexistente, e os recursos GTK,
ícones e cursor referenciados não eram instalados/aplicados. O diagnóstico e
as demais causas estão em [DIAGNOSTICO.md](docs/DIAGNOSTICO.md).

## Instalar ou atualizar na VM

Repositório público: [Ronilsondev/gh0stzk-hyprland](https://github.com/Ronilsondev/gh0stzk-hyprland).
Na VM Arch, como usuário comum, baixe somente o instalador em um diretório novo.
Resolva `main` uma vez para um SHA completo e use a mesma revisão no download
e no bootstrap (requer `curl`; `git` é usado aqui apenas para resolver a revisão):

```bash
repo=https://github.com/Ronilsondev/gh0stzk-hyprland
ref=$(git ls-remote "$repo" refs/heads/main | cut -f1)
[[ $ref =~ ^[0-9a-f]{40}$ ]] || { echo 'Referência não encontrada'; exit 1; }
dir=$(mktemp -d "$HOME/gh0stzk-installer.XXXXXXXX")
cd "$dir"
curl --fail --show-error --location --proto '=https' --proto-redir '=https' \
  "https://raw.githubusercontent.com/Ronilsondev/gh0stzk-hyprland/$ref/instalar.sh" \
  -o instalar.sh
bash instalar.sh --ref "$ref" --dry-run
bash instalar.sh --ref "$ref"
```

O dry-run avulso é offline e informa seus limites: não consegue conferir os
manifests sem baixar o restante do projeto. No fluxo real, o instalador obtém
um único commit por HTTPS. Também é possível usar uma cópia completa e executar
`bash instalar.sh --dry-run` antes de `bash instalar.sh`; uma cópia local não
é atualizada automaticamente por `--ref`. A instalação real é exclusiva da VM.

O fluxo faz atualização total Arch com `pacman -Syu --needed`, instala os
componentes padrão, obtém os recursos externos fixados, valida e aplica os
arquivos com backup, registra a sessão e gera o tema inicial. Não encerra a
sessão atual, não substitui o gerenciador de login e não instala no ambiente
principal durante testes deste repositório.

Eww, Hyprpicker, checkupdates, GTK, ícones e cursor são parte da instalação
padrão. Eww é compilado como usuário comum se necessário. Recursos externos
usam HTTPS e SHA-256, sem adicionar o repositório HTTP do autor ao pacman.
[Dependências, licenças e matriz recurso → pacote → configuração → inicialização](docs/DEPENDENCIAS.md).

Alguns ícones originais têm links quebrados; a lista exata é salva em
`~/.local/share/gh0stzk-hyprland-visuals/current/report.json`. Fontes foram
normalizadas para famílias licenciadas disponíveis. GTK 4/libadwaita não
promete reproduzir o CSS GTK 3 original. Essas limitações não são escondidas
por uma mensagem de “aparência completa”. Falhas de dependências obrigatórias
interrompem o fluxo.

## Retomar após falha de compilação do Eww

O erro `E0282: type annotations needed for Box<_>` em `time 0.3.34` é corrigido
pela receita local no `prepare()`, depois da extração e antes do build. A linha
`time 0.3` passa a exigir pelo menos `0.3.36`; a dependência legada `time 0.1.45`
é distinta e permanece. A correção sobrevive a `makepkg --cleanbuild`, preserva
SHA-256/licença MIT e usa cache Cargo privado. Veja [detalhes](docs/DEPENDENCIAS.md#eww).

Para retomar **uma revisão específica**, use o SHA completo publicado da
correção no lugar do marcador abaixo, tanto na URL quanto em `--ref`:

```bash
ref=SHA_COMPLETO_PUBLICADO
[[ $ref =~ ^[0-9a-f]{40}$ ]] || { echo 'Substitua pelo SHA publicado'; exit 1; }
dir=$(mktemp -d "$HOME/gh0stzk-installer.XXXXXXXX")
curl --fail --show-error --location --proto '=https' --proto-redir '=https' \
  "https://raw.githubusercontent.com/Ronilsondev/gh0stzk-hyprland/$ref/instalar.sh" \
  -o "$dir/instalar.sh"
bash "$dir/instalar.sh" --ref "$ref" --dry-run
bash "$dir/instalar.sh" --ref "$ref"
```

Execute na VM Arch, **sem sudo bash**, com as mesmas opções da tentativa
anterior. O diretório novo evita executar uma cópia antiga completa: `--ref`
não atualiza seu checkout. O dry-run avulso continua offline, com os limites
explicados acima; no fluxo real o restante do projeto vem do mesmo SHA.

A transação de pacman anterior pode ter atualizado/instalado pacotes antes da
falha. Repetir o fluxo usa `-Syu --needed`, não desfaz essas etapas. Nesta revisão,
o Eww é compilado antes de aplicar os dotfiles, mas outra tentativa pode já
ter criado backup. **Não apague nem restaure esse backup para simplesmente
continuar.** Preferências (`local.lua`, `preferences.json`, overrides e tema
escolhido) são preservadas. Arquivos gerenciados alterados localmente causam
recusa explícita: guarde uma cópia e resolva apenas o arquivo indicado, sem
reset forçado. Não existe opção `--skip-config` e não é necessário remover
configurações ou modificar o cache global do Cargo. Restauração é uma decisão
separada, usando o backup exato e a inspeção descrita abaixo; ela não remove
pacotes nem desfaz serviços.

## Entrar na sessão

Saia voluntariamente e selecione **Hyprland — gh0stzk** no gerenciador de login.
A entrada genérica Hyprland continua disponível para a configuração anterior.
Alternativamente, em TTY fora de uma sessão gráfica:

```bash
~/.local/bin/gh0stzk-session
```

Emilia é o tema inicial; uma atualização mantém a seleção anterior. Barras,
wallpaper, notificações e daemon Eww iniciam ao entrar. Menus e widgets abrem
pelos atalhos/botões. Super+Enter abre o Kitty com a configuração do tema;
Super+Espaço abre aplicativos; Alt+Espaço escolhe o tema.

```bash
~/.local/bin/gh0stzk list
~/.local/bin/gh0stzk theme emilia
~/.local/bin/gh0stzk widget launchermenu
~/.local/bin/gh0stzk widget music
~/.local/bin/gh0stzk diagnose > ~/gh0stzk-diagnostico.json
```

[Ensaio da sessão na VM](docs/SESSAO.md) · [Atalhos](docs/ATALHOS.md).
Para continuar a investigação, envie inicialmente apenas o JSON do diagnóstico.

## Preferências e backups

Edite `~/.config/gh0stzk-hyprland/local.lua` e `preferences.json`. Eles são
preservados ao atualizar, assim como overrides e wallpaper escolhido. Se
`widgets` já estiver `false`, continua desativado até você mudar para `true`.
GTK/GSettings usam um perfil privado da sessão; as configurações globais de
KDE, GNOME, Kitty, shell e outros ambientes permanecem preservadas.

Backups: `~/.local/state/gh0stzk-hyprland/backups`. Alterações suas em arquivos
gerenciados são detectadas e recusam sobrescrita. Para restaurar arquivos,
fora da sessão, use o caminho exato informado na instalação:

```bash
python3 ~/.local/share/gh0stzk-hyprland/install.py --restore CAMINHO_DO_BACKUP
python3 ~/.local/share/gh0stzk-hyprland/install.py --restore CAMINHO_DO_BACKUP --apply
```

Arquivos modificados posteriormente são preservados (saída 2). Pacotes,
serviços e armazenamento externo de recursos não são removidos. Gerações de
tema ficam disponíveis para `gh0stzk rollback --offline` no TTY.

## Opções

`bash instalar.sh --help` descreve o fluxo. `--yes` dispensa a confirmação
inicial, mas não autenticação sudo ou decisões do pacman.

| Opção | Efeito |
|---|---|
| `--dry-run` | Plano sem downloads, instalações ou escritas |
| `--repo URL --ref REF` | Origem da adaptação no modo avulso; nunca o BSPWM upstream |
| `--optional PACOTE` | Bluetooth (`blueman`, `bluez`, `bluez-utils`), `uwsm` ou `shellcheck` |
| `--with-eww ARQUIVO` | Usa um pacote local Eww com suporte Wayland |
| `--without-fonts` | Exclusão explícita das fontes incluídas; pode deixar a tipografia incompleta |
| `--without-portals` | Não instala a preferência específica de portais |
| `--without-session` | Não registra entrada no login; início pelo TTY |

## Verificar sem instalar

```bash
python3 -m unittest discover -s tests -v
python3 tools/validate.py --report /tmp/gh0stzk-validacao.json
bash instalar.sh --dry-run
```

A suíte usa homes temporárias e comandos administrativos simulados.
`install.py --allow-missing` é só preparação de arquivos; não é o instalador
completo. Nenhum desses comandos abre uma sessão gráfica.

[Validação e limites](docs/VALIDACAO.md) · [Temas](docs/TEMAS.md) ·
[Migração](docs/MIGRACAO.md) · [Uso](docs/USO.md) · [Fontes técnicas](docs/FONTES.md).
