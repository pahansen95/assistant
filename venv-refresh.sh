#!/usr/bin/env fish

if ! status --is-interactive
  echo "The file was not sourced." >&2
end

if test -z CI_PROJECT_DIR
  echo "CI_PROJECT_DIR not found, set in .envrc" >&2
  return 1
end

if command -v deactivate &>/dev/null
  deactivate
end

bash $CI_PROJECT_DIR/venv-rebuild.sh

source $CI_PROJECT_DIR/.venv/bin/activate.fish