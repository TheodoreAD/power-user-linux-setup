local wezterm = require "wezterm"
local mux = wezterm.mux
local config = wezterm.config_builder()

config.font = wezterm.font "CaskaydiaCove NFM"
config.font_size = 12.0

-- Start maximized with a 50/50 vertical split; right pane gets focus
wezterm.on("gui-startup", function(cmd)
  local tab, pane, window = mux.spawn_window(cmd or {})
  local right_pane = pane:split { direction = "Right", size = 0.5 }
  window:gui_window():maximize()
  right_pane:activate()
end)

return config
