#!/usr/bin/env bash

: "${CI_PROJECT_DIR:?"CI_PROJECT_DIR not found, set in .envrc"}"

if command -v deactivate &>/dev/null; then
  deactivate
fi

rm -rf "${CI_PROJECT_DIR}/.venv"

python3 -m venv "${CI_PROJECT_DIR}/.venv"

source "${CI_PROJECT_DIR}/.venv/bin/activate"

pip install --upgrade pip

declare temp_requirements_file; temp_requirements_file="$(mktemp)"; trap 'rm -f "${temp_requirements_file}"' EXIT; declare -r temp_requirements_file
poetry export > "${temp_requirements_file}"

pip install -r "${temp_requirements_file}"
