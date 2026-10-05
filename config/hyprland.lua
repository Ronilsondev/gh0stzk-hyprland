-- Adaptação independente gh0stzk → Hyprland 0.56; GPL-3.0.
local config_home = os.getenv('XDG_CONFIG_HOME') or (os.getenv('HOME') .. '/.config')
local state_home = os.getenv('XDG_STATE_HOME') or (os.getenv('HOME') .. '/.local/state')
local data_home = os.getenv('XDG_DATA_HOME') or (os.getenv('HOME') .. '/.local/share')
local project = os.getenv('GH0STZK_ROOT') or (data_home .. '/gh0stzk-hyprland')
local current = state_home .. '/gh0stzk-hyprland/current'
local function quote(s) return "'" .. s:gsub("'", "'\\''") .. "'" end
local ctl = quote(project .. '/bin/gh0stzk')
local reserved = dofile(current .. '/theme.lua')
hl.monitor({output = '', mode = 'preferred', position = 'auto', scale = 'auto', reserved_area = reserved})
hl.config({input = {kb_layout = 'us', follow_mouse = 1}, general = {resize_on_border = true}})
hl.env('XDG_CURRENT_DESKTOP', 'Hyprland')
hl.env('XDG_SESSION_DESKTOP', 'Hyprland')
hl.env('XDG_SESSION_TYPE', 'wayland')
local function app(keys, command, desc, flags)
    local f = flags or {}
    f.description = desc
    hl.bind(keys, hl.dsp.exec_cmd(ctl .. ' ' .. command), f)
end
app('SUPER + Return', 'app terminal', 'Terminal')
app('SUPER + ALT + Return', 'app floating', 'Terminal flutuante')
app('SUPER + space', 'launcher', 'Aplicativos')
app('ALT + space', 'theme', 'Selecionar tema')
app('SUPER + ALT + w', 'wallpaper', 'Selecionar wallpaper')
app('SUPER + f', 'app files', 'Arquivos')
app('SUPER + b', 'app browser', 'Navegador')
app('SUPER + p', 'app mixer', 'Mixer de áudio')
app('SUPER + r', 'edit-theme', 'Editor de aparência')
app('SUPER + ALT + n', 'network', 'Rede')
app('SUPER + ALT + b', 'bluetooth', 'Bluetooth')
app('SUPER + ALT + c', 'clipboard', 'Clipboard')
app('SUPER + ALT + s', 'screenshot menu', 'Captura de tela')
app('Print', 'screenshot full', 'Captura completa')
app('SHIFT + Print', 'screenshot region', 'Capturar região')
app('ALT + Print', 'screenshot window', 'Capturar janela focada')
app('SUPER + ALT + p', 'power', 'Sessão e energia')
app('SUPER + CTRL + l', 'lock', 'Bloquear')
app('SUPER + ALT + o', 'scratch', 'Scratchpad')
app('ALT + F1', 'help', 'Guia de atalhos')
app('ALT + Tab', 'windows', 'Alternar janela')
app('SUPER + ALT + l', 'launcher-style', 'Estilo do launcher')
app('SUPER + ALT + k', 'keyboard', 'Alternar teclado')
app('SUPER + ALT + h', 'bar hide', 'Ocultar barras')
app('SUPER + ALT + u', 'bar show', 'Mostrar barras')
app('SUPER + ALT + r', 'refresh', 'Recarregar tema e monitores')
app('SUPER + CTRL + ALT + p', 'power desligar', 'Desligar com confirmação')
app('SUPER + CTRL + ALT + r', 'power reiniciar', 'Reiniciar com confirmação')
app('SUPER + CTRL + ALT + q', 'power sair', 'Sair com confirmação')
for _, binding in ipairs({
    {'XF86AudioRaiseVolume', 'volume up'}, {'XF86AudioLowerVolume', 'volume down'},
    {'XF86AudioMute', 'volume mute'}, {'XF86AudioMicMute', 'volume mic'},
    {'XF86MonBrightnessUp', 'brightness up'}, {'XF86MonBrightnessDown', 'brightness down'},
    {'XF86AudioPlay', 'media play-pause'}, {'XF86AudioNext', 'media next'},
    {'XF86AudioPrev', 'media previous'}, {'XF86AudioStop', 'media stop'}
}) do app(binding[1], binding[2], binding[2], {repeating = true, locked = true}) end
hl.bind('SUPER + x', hl.dsp.window.close())
hl.bind('SUPER + SHIFT + space', hl.dsp.window.float())
hl.bind('SUPER + F11', hl.dsp.window.fullscreen())
hl.bind('SUPER + m', hl.dsp.window.fullscreen({mode = 'maximized'}))
for _, pair in ipairs({{'Left', 'left'}, {'Right', 'right'}, {'Up', 'up'}, {'Down', 'down'}}) do
    hl.bind('SUPER + ' .. pair[1], hl.dsp.focus({direction = pair[2]}))
    hl.bind('SUPER + SHIFT + ' .. pair[1], hl.dsp.window.move({direction = pair[2]}))
end
for i = 1, 9 do
    hl.bind('SUPER + ' .. i, hl.dsp.focus({workspace = tostring(i)}))
    hl.bind('SUPER + SHIFT + ' .. i, hl.dsp.window.move({workspace = tostring(i)}))
end
hl.bind('SUPER + comma', hl.dsp.focus({monitor = '-1'}))
hl.bind('SUPER + period', hl.dsp.focus({monitor = '+1'}))
hl.bind('SUPER + SHIFT + comma', hl.dsp.window.move({monitor = '-1'}))
hl.bind('SUPER + SHIFT + period', hl.dsp.window.move({monitor = '+1'}))
hl.bind('SUPER + mouse:272', hl.dsp.window.drag(), {mouse = true})
hl.bind('SUPER + mouse:273', hl.dsp.window.resize(), {mouse = true})
hl.window_rule({match = {class = 'gh0stzk-scratch'}, workspace = 'special:gh0stzk silent', float = true,
                size = {'(monitor_w*0.65)', '(monitor_h*0.65)'}, center = true})
hl.window_rule({match = {class = 'gh0stzk-floating'}, float = true, center = true,
                size = {'(monitor_w*0.55)', '(monitor_h*0.5)'}})
hl.window_rule({match = {class = '(org.pulseaudio.pavucontrol|pavucontrol|nm-connection-editor|blueman-manager)'},
                float = true, center = true})
-- Preferências do usuário são aplicadas por último, inclusive regras específicas de monitores.
local localfile = config_home .. '/gh0stzk-hyprland/local.lua'
local f = io.open(localfile)
if f then f:close(); dofile(localfile) end
hl.on('hyprland.start', function() hl.exec_cmd(ctl .. 'session') end)
