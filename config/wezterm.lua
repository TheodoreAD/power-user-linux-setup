local wezterm = require "wezterm"
local act = wezterm.action
local mux = wezterm.mux
local config = wezterm.config_builder()

config.font = wezterm.font "CaskaydiaCove NFM"
config.font_size = 12.0

-- Start maximized with a 2x2 grid of panes; top-left gets focus.
-- Split order matters: panes are indexed by their position in the split tree
-- (left-to-right, top-to-bottom), so building the row divider first keeps the
-- indices matching reading order — 0 top-left, 1 top-right, 2 bottom-left,
-- 3 bottom-right — which is what the ALT+<n> bindings below rely on.
wezterm.on("gui-startup", function(cmd)
  local _tab, top_left, window = mux.spawn_window(cmd or {})
  local bottom_left = top_left:split { direction = "Bottom", size = 0.5 }
  top_left:split { direction = "Right", size = 0.5 }
  bottom_left:split { direction = "Right", size = 0.5 }
  window:gui_window():maximize()
  top_left:activate()
end)

config.keys = {
  -- Cycle panes in index order, the way CTRL+Tab cycles tabs. CTRL+Tab is a
  -- duplicate of CTRL+PageDown in the defaults, so tab cycling loses nothing by
  -- handing the Tab chord over to panes.
  { key = "Tab", mods = "CTRL", action = act.ActivatePaneDirection "Next" },
  { key = "Tab", mods = "CTRL|SHIFT", action = act.ActivatePaneDirection "Prev" },

  -- Jump straight to a pane of the 2x2 grid.
  { key = "1", mods = "ALT", action = act.ActivatePaneByIndex(0) },
  { key = "2", mods = "ALT", action = act.ActivatePaneByIndex(1) },
  { key = "3", mods = "ALT", action = act.ActivatePaneByIndex(2) },
  { key = "4", mods = "ALT", action = act.ActivatePaneByIndex(3) },

  -- Resize the focused pane without the default three-modifier chord.
  { key = "LeftArrow", mods = "ALT|SHIFT", action = act.AdjustPaneSize { "Left", 3 } },
  { key = "RightArrow", mods = "ALT|SHIFT", action = act.AdjustPaneSize { "Right", 3 } },
  { key = "UpArrow", mods = "ALT|SHIFT", action = act.AdjustPaneSize { "Up", 3 } },
  { key = "DownArrow", mods = "ALT|SHIFT", action = act.AdjustPaneSize { "Down", 3 } },
}

return config
