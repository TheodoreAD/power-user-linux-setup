#!/bin/bash
# Approximates the p10k setup from ~/.p10k.zsh (left: dir, vcs; right: virtualenv/anaconda).
# user@host (p10k "context" segment) intentionally omitted.
# Colors mirror p10k's own FOREGROUND numbers: dir=blue(4), vcs clean=green(2)/dirty=yellow(3),
# virtualenv/anaconda=cyan(6). Rate-limit/time-of-day text=dark gold(256-color 136).
#
# Model name, context-window fill, both rate-limit windows, and session cost all share
# one muted 256-color "weight" palette (gray -> green -> orange -> red, low to high,
# via the tier_color() function) instead of loud ANSI colors, so the line stays easy
# on the eyes:
#   - model name: haiku=gray, sonnet=green, opus=orange, fable=red (heaviest — sits
#     above opus in the model-fallback chain).
#   - context window (shown as tokens in K, not %, with a pie glyph ○ ◔ ◑ ◕ ● reflecting
#     fill % of the actual window): color is by ABSOLUTE token count, not %, since
#     Anthropic's own /usage page flags ">150k context" as more expensive regardless of
#     window size (cache read/write cost scales with tokens processed, not window
#     fraction) — gray <75k, green 75-150k, orange 150-300k (warning, matches that real
#     150k figure), red >=300k (WTF). Deliberately its own breakpoints, not
#     tier_color()'s generic percentage-based ones.
#   - 5h/7d rate-limit windows: each independently colored by its own used_percentage
#     via the generic tier_color() (gray<13%, green 13-50%, orange 50-75%, red >=75%).
#   - session cost ("$", rounded up to whole dollars): gray <$5, green $5-15, orange
#     $15-30, red >=$30.
# Icons pulled from powerlevel10k's own nerdfont-complete icon table
# (~/.oh-my-zsh/custom/themes/powerlevel10k/internal/icons.zsh — matches
# POWERLEVEL9K_MODE=nerdfont-complete set in ~/.p10k.zsh):
#   HOME_ICON, HOME_SUB_ICON, FOLDER_ICON, VCS_BRANCH_ICON, PYTHON_ICON,
#   TIME_ICON (current time), EXECUTION_TIME_ICON (hourglass, 5h window),
#   and Font Awesome's calendar glyph (7d window). The staged/unstaged/untracked/
#   ahead/behind counts use plain ASCII/Unicode (+ ! ? ↑ ↓, oh-my-zsh style) — more
#   readable than their nerd-font glyph equivalents at small counts.

home_icon=$(printf '\xEF\x80\x95')
home_sub_icon=$(printf '\xEF\x81\xBC')
folder_icon=$(printf '\xEF\x84\x95')
branch_icon=$(printf '\xEF\x84\xA6')
staged_icon='+'
unstaged_icon='!'
untracked_icon='?'
outgoing_icon=$(printf '\xE2\x86\x91') # ↑ (plain Unicode, not nerd-font-only)
incoming_icon=$(printf '\xE2\x86\x93') # ↓ (plain Unicode, not nerd-font-only)
python_icon=$(printf '\xEE\x9C\xBC')
time_icon=$(printf '\xEF\x80\x97')
clock_icon=$(printf '\xEF\x89\x92')
calendar_icon=$(printf '\xEF\x81\xB3')
pie_0_icon=$(printf '\xE2\x97\x8B')   # ○ empty
pie_25_icon=$(printf '\xE2\x97\x94')  # ◔ quarter
pie_50_icon=$(printf '\xE2\x97\x91')  # ◑ half
pie_75_icon=$(printf '\xE2\x97\x95')  # ◕ three-quarter
pie_100_icon=$(printf '\xE2\x97\x8F') # ● full

# shared muted 4-tier "weight" palette (256-color, deliberately low-saturation —
# reused identically for model name, context-window fill, and session cost)
tier_gray='38;5;244'
tier_green='38;5;65'
tier_orange='38;5;172'
tier_red='38;5;131'

# maps a 0-100 usage percentage to one of the tier colors above (gray<13, green<50,
# orange<75, red>=75) — shared by context-window fill and both rate-limit windows,
# each evaluated independently against its own percentage.
tier_color() {
  local pct=$1
  if awk -v p="$pct" 'BEGIN{exit !(p>=75)}'; then
    echo "$tier_red"
  elif awk -v p="$pct" 'BEGIN{exit !(p>=50)}'; then
    echo "$tier_orange"
  elif awk -v p="$pct" 'BEGIN{exit !(p>=13)}'; then
    echo "$tier_green"
  else
    echo "$tier_gray"
  fi
}

input=$(cat)
cwd=$(echo "$input" | jq -r '.workspace.current_dir')

# dir: collapse $HOME to ~, prefixed with p10k's home/home-sub/folder icon
dir=${cwd/#$HOME/\~}
if [ "$cwd" = "$HOME" ]; then
  dir_icon=$home_icon
elif [ "${cwd#"$HOME"/}" != "$cwd" ]; then
  dir_icon=$home_sub_icon
else
  dir_icon=$folder_icon
fi

# vcs: git branch (green if clean, yellow if dirty) plus oh-my-zsh-style counts —
# staged/unstaged/untracked/ahead(unpushed)/behind(unpulled), each shown only when nonzero.
git_segment=""
if git -C "$cwd" rev-parse --is-inside-work-tree > /dev/null 2>&1; then
  branch=$(git -C "$cwd" symbolic-ref --quiet --short HEAD 2> /dev/null || git -C "$cwd" rev-parse --short HEAD 2> /dev/null)
  if [ -n "$branch" ]; then
    status_v2=$(git -C "$cwd" status --porcelain=v2 --branch 2> /dev/null)
    staged_count=$(printf '%s\n' "$status_v2" | awk '$1=="1"||$1=="2"{if (substr($2,1,1)!=".") c++} END{print c+0}')
    unstaged_count=$(printf '%s\n' "$status_v2" | awk '$1=="1"||$1=="2"{if (substr($2,2,1)!=".") c++} END{print c+0}')
    untracked_count=$(printf '%s\n' "$status_v2" | awk '$1=="?"{c++} END{print c+0}')
    ahead_count=$(printf '%s\n' "$status_v2" | awk '/^# branch\.ab/{gsub(/\+/,"",$3); print $3+0; f=1} END{if(!f) print 0}')
    behind_count=$(printf '%s\n' "$status_v2" | awk '/^# branch\.ab/{gsub(/-/,"",$4); print $4+0; f=1} END{if(!f) print 0}')

    if [ "$staged_count" -gt 0 ] || [ "$unstaged_count" -gt 0 ] || [ "$untracked_count" -gt 0 ]; then
      git_color=33 # dirty: yellow
    else
      git_color=32 # clean: green
    fi

    counts=""
    [ "$staged_count" -gt 0 ] && counts="$counts $staged_icon$staged_count"
    [ "$unstaged_count" -gt 0 ] && counts="$counts $unstaged_icon$unstaged_count"
    [ "$untracked_count" -gt 0 ] && counts="$counts $untracked_icon$untracked_count"
    [ "$ahead_count" -gt 0 ] && counts="$counts $outgoing_icon$ahead_count"
    [ "$behind_count" -gt 0 ] && counts="$counts $incoming_icon$behind_count"

    git_segment=$(printf ' \033[%sm%s %s%s\033[00m' "$git_color" "$branch_icon" "$branch" "$counts")
  fi
fi

# virtualenv (with python version) / conda env
env_segment=""
if [ -n "$VIRTUAL_ENV" ]; then
  py_version=$("$VIRTUAL_ENV/bin/python3" --version 2> /dev/null | awk '{print $2}')
  env_name=$(basename "$VIRTUAL_ENV")
  if [ -n "$py_version" ]; then
    env_segment=$(printf ' \033[36m%s %s %s\033[00m' "$python_icon" "$env_name" "$py_version")
  else
    env_segment=$(printf ' \033[36m%s %s\033[00m' "$python_icon" "$env_name")
  fi
elif [ -n "$CONDA_DEFAULT_ENV" ]; then
  env_segment=$(printf ' \033[36m%s %s\033[00m' "$python_icon" "$CONDA_DEFAULT_ENV")
fi

# rate limits (Claude.ai Pro/Max subscription usage): remaining % + local reset time.
# Absent entirely for API-key auth / non-Pro/Max, in which case this segment is omitted.
five_used=$(echo "$input" | jq -r '.rate_limits.five_hour.used_percentage // empty')
five_reset=$(echo "$input" | jq -r '.rate_limits.five_hour.resets_at // empty')
seven_used=$(echo "$input" | jq -r '.rate_limits.seven_day.used_percentage // empty')
seven_reset=$(echo "$input" | jq -r '.rate_limits.seven_day.resets_at // empty')

five_part=""
if [ -n "$five_used" ] && [ -n "$five_reset" ]; then
  five_remaining=$(awk -v u="$five_used" 'BEGIN { printf "%.0f", 100 - u }')
  five_time=$(date -d "@$five_reset" '+%H:%M' 2> /dev/null)
  if [ -n "$five_time" ]; then
    five_color=$(tier_color "$five_used")
    five_part=$(printf ' \033[%sm%s %s%% %s\033[00m' "$five_color" "$clock_icon" "$five_remaining" "$five_time")
  fi
fi

seven_part=""
if [ -n "$seven_used" ] && [ -n "$seven_reset" ]; then
  seven_remaining=$(awk -v u="$seven_used" 'BEGIN { printf "%.0f", 100 - u }')
  seven_day=$(LC_TIME=C date -d "@$seven_reset" '+%a' 2> /dev/null)
  if [ -n "$seven_day" ]; then
    seven_color=$(tier_color "$seven_used")
    seven_part=$(printf ' \033[%sm%s %s%% %s\033[00m' "$seven_color" "$calendar_icon" "$seven_remaining" "$seven_day")
  fi
fi

rate_segment=""
if [ -n "$five_part" ] || [ -n "$seven_part" ]; then
  now_str=$(printf '%s %s' "$time_icon" "$(LC_TIME=C date '+%H:%M %a')")
  now_segment=$(printf ' \033[38;5;136m%s\033[00m' "$now_str")
  rate_segment="$now_segment$five_part$seven_part"
fi

# context window usage: pie-slice glyph (empty/quarter/half/three-quarter/full) + token
# count in K, colored green/yellow/red by fill %. Omitted until the first API response.
ctx_segment=""
ctx_pct=$(echo "$input" | jq -r '.context_window.used_percentage // empty')
if [ -n "$ctx_pct" ]; then
  ctx_round=$(awk -v p="$ctx_pct" 'BEGIN { printf "%.0f", p }')
  ctx_tokens=$(echo "$input" | jq -r '.context_window.total_input_tokens // 0')
  ctx_k=$(LC_NUMERIC=C awk -v t="$ctx_tokens" 'BEGIN { printf "%.0f", t/1000 }')
  if [ "$ctx_round" -ge 88 ]; then
    ctx_icon=$pie_100_icon
  elif [ "$ctx_round" -ge 63 ]; then
    ctx_icon=$pie_75_icon
  elif [ "$ctx_round" -ge 38 ]; then
    ctx_icon=$pie_50_icon
  elif [ "$ctx_round" -ge 13 ]; then
    ctx_icon=$pie_25_icon
  else
    ctx_icon=$pie_0_icon
  fi
  if [ "$ctx_tokens" -ge 300000 ]; then
    ctx_color=$tier_red # WTF: well past the point cost/quality suffer
  elif [ "$ctx_tokens" -ge 150000 ]; then
    ctx_color=$tier_orange # warning: Anthropic's own usage page flags >150k as more expensive, regardless of window size
  elif [ "$ctx_tokens" -ge 75000 ]; then
    ctx_color=$tier_green
  else
    ctx_color=$tier_gray
  fi
  ctx_segment=$(printf ' \033[%sm%s %sK\033[00m' "$ctx_color" "$ctx_icon" "$ctx_k")
fi

# current model name — colored by weight class, so a heavier model stands out
model_segment=""
model_name=$(echo "$input" | jq -r '.model.display_name // empty')
if [ -n "$model_name" ]; then
  case "$(echo "$model_name" | tr '[:upper:]' '[:lower:]')" in
    *haiku*) model_color=$tier_gray ;;
    *sonnet*) model_color=$tier_green ;;
    *opus*) model_color=$tier_orange ;;
    *fable*) model_color=$tier_red ;;
    *) model_color=$tier_gray ;; # unknown model
  esac
  model_segment=$(printf ' \033[%sm%s\033[00m' "$model_color" "$model_name")
fi

# session running cost (estimated, client-side), rounded up to the nearest whole dollar.
cost_segment=""
cost_usd=$(echo "$input" | jq -r '.cost.total_cost_usd // empty')
if [ -n "$cost_usd" ]; then
  cost_whole=$(LC_NUMERIC=C awk -v c="$cost_usd" 'BEGIN { n = int(c); if (c > n) n++; printf "%d", n }')
  if awk -v c="$cost_usd" 'BEGIN{exit !(c>=30)}'; then
    cost_color=$tier_red
  elif awk -v c="$cost_usd" 'BEGIN{exit !(c>=15)}'; then
    cost_color=$tier_orange
  elif awk -v c="$cost_usd" 'BEGIN{exit !(c>=5)}'; then
    cost_color=$tier_green
  else
    cost_color=$tier_gray
  fi
  cost_segment=$(printf ' \033[%sm$%s\033[00m' "$cost_color" "$cost_whole")
fi

printf '\033[34m%s %s\033[00m%s%s%s%s%s%s' "$dir_icon" "$dir" "$git_segment" "$env_segment" "$rate_segment" "$ctx_segment" "$cost_segment" "$model_segment"
