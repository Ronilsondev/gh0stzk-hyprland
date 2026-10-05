# Teste em máquina virtual e sessão gráfica

Os testes desta cópia foram feitos na sessão KDE/X11/Wayland existente sem
substituí-la. Hyprland, Waybar, Rofi, Dunst, Eww, Hyprlock e Hypridle não estão
instalados. Não houve sessão de teste, captura comparativa final, screenshot
Hyprlock, screenshot de cada barra nem teste de portal real. Veja
`VALIDACAO.md`.

Para testar com segurança numa VM Arch:

1. Use um snapshot e instale uma sessão Arch atualizada, Mesa/OpenGL funcional,
   PipeWire e driver apropriado ao dispositivo virtual. As flags de aceleração
   3D e o renderizador variam com VirtualBox, QEMU/KVM e VMware; sem DRM/GL
   funcional, Hyprland pode encerrar no startup. Confirme que a VM recebe um
   output Wayland útil e teste resolução antes de avaliar pixels.
2. Rode o instalador completo de uma vez, que atualiza o sistema, instala os
   pacotes oficiais e aplica os arquivos com backup:

   ```bash
   curl -fLO https://raw.githubusercontent.com/SEU_USUARIO/SEU_REPO/main/instalar.sh
   bash instalar.sh --dry-run     # leia o plano antes
   bash instalar.sh
   ```

   Se preferir separar as etapas, veja a
   [sequência manual](#sequência-manual-se-você-não-quiser-usar-o-instalador)
   no fim deste arquivo.
3. Inicie em TTY com `~/.local/bin/gh0stzk-session`, ou saia e escolha
   "Hyprland — gh0stzk" no gerenciador de login. Mantenha uma TTY/console
   virtual disponível para recuperar o tema caso algum driver falhe.
4. Teste launcher/Rofi, mudança de tema, restauração, escala, foco da barra,
   captura por região e por janela, fechamento de tampa/idle, lock antes de
   suspender, desbloqueio, clipboard de texto/imagem, áudio, notification D-Bus,
   monitor virtual e iniciar/parar um portal de screen share.
5. Compare `hyprctl monitors all` e `hyprctl configerrors`. Capture cada tema
   em tamanhos conhecidos e cote `preview.webp`. Registre substituições de fonte,
   altura/overlap dos módulos, offsets e widgets Eww.

Esperado em uma VM: desempenho modesto em cena animada, blur e sombras com
mais impacto. Se Hyprland encerrar no início, quase sempre é DRM/GL da VM, não
a configuração; `hyprctl configerrors` e `~/.local/state/gh0stzk-hyprland/*.log`
separam as duas coisas.

No Arch gráfico já funcional, prefira criar um usuário temporário. O teste de
resolução/VM não é uma validação de drivers de notebook nem de GPU dedicada.
Não execute o instalador original.

## Sequência manual, se você não quiser usar o instalador

O `instalar.sh` é o caminho recomendado, mas os passos que ele executa podem
ser feitos à mão. **Atualize o sistema inteiro primeiro** — o Arch proíbe
atualização parcial:

```bash
sudo pacman -Syu --needed
python3 install.py                       # dry-run; leia antes de aplicar
sudo pacman -Syu --needed -- $(python3 -c 'import json; print(" ".join(json.load(open("packages.json"))["official"]))')
python3 install.py --apply --with-fonts --with-portals --with-session
fc-cache -f "$HOME/.local/share/fonts/gh0stzk-hyprland"
```

`--with-session` registra a entrada no gerenciador de login e exige `sudo` uma
vez, com journal em `/var/lib/gh0stzk-hyprland/sessions`. Omitir `--with-session`
mantém o início manual por TTY como única forma de entrar.

Para inspeção estática sem GUI:

```bash
python3 tools/validate.py --render-dir /tmp/gh0stzk-renderizados
```

Isso deixa JSON, CSS, Rasi, Hyprlock, Kitty e Dunst por tema em `/tmp`; não
inicia compositor ou clientes Wayland. Após instalar Hyprland 0.56, o comando
também chama `Hyprland --verify-config` com HOME temporária, quando detecta a
opção na compilação. Esse modo checa arquivo/configuração, não cria sessão gráfica.
