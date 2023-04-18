#!/usr/bin/env bash

set -eEuo pipefail

log() {
  echo "[$(date -u)] $*" >&2
}

if [[ "$(id -u)" -ne 0 ]]; then
  log "This script must be run as root"
fi

case "$(uname -m)" in
  x86_64)
    declare -r \
      headscale_url="https://github.com/juanfont/headscale/releases/download/v0.21.0/headscale_0.21.0_linux_amd64" \
      caddy_url="https://caddyserver.com/api/download?os=linux&arch=amd64" \
      sws_url="https://github.com/static-web-server/static-web-server/releases/download/v2.15.0/static-web-server-v2.15.0-x86_64-unknown-linux-gnu.tar.gz"
    ;;
  aarch64)
    declare -r \
      headscale_url="https://github.com/juanfont/headscale/releases/download/v0.21.0/headscale_0.21.0_linux_arm64" \
      caddy_url="https://caddyserver.com/api/download?os=linux&arch=arm64" \
      sws_url="https://github.com/static-web-server/static-web-server/releases/download/v2.15.0/static-web-server-v2.15.0-aarch64-unknown-linux-gnu.tar.gz"
    ;;
  *)
    log "Unsupported architecture: $(uname -m)"
    exit 1
    ;;
esac

declare -r \
  headscale_ui_tag="${HEADSCALE_UI_TAG:-"2023.01.30-beta-1"}"

apt-get update -y
apt-get install -y --no-install-recommends\
  ca-certificates \
  git \
  curl \
  jq \
  sed

### Installing Node.JS, NPM & NVM ###
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.3/install.sh | bash
export NVM_DIR="$HOME/.nvm"
source "$NVM_DIR/nvm.sh"
nvm install node

### Install headscale ###
curl -L "${headscale_url}" -o /usr/local/bin/headscale
chmod +x /usr/local/bin/headscale
if [[ "$(command -v headscale)" != "/usr/local/bin/headscale" ]]; then
  log "headscale failed to install"
  exit 1
fi

### Install headscale's UI ###
mkdir -p "/tmp/headscale-ui"
git clone \
  --depth 1 --single-branch \
  --branch "${headscale_ui_tag}" \
  https://github.com/gurucomputing/headscale-ui.git \
  /tmp/headscale-ui
(
  set -eEuo pipefail
  cd /tmp/headscale-ui
  npm install
  sed -i \
    "s/insert-version/$(jq -r '.version' package.json)/g" \
    ./src/routes/settings.html/+page.svelte
  npm run build
)
mv /tmp/headscale-ui/build/* /var/www/web
ln  /var/www/web/index.html /var/www/index.html

# ### Install Caddy ###
# curl -L "${caddy_url}" -o /usr/local/bin/caddy
# chmod +x /usr/local/bin/caddy
# if [[ "$(command -v caddy)" != "/usr/local/bin/caddy" ]]; then
#   log "caddy failed to install"
#   exit 1
# fi

### Install Simple Web Server ###
curl -L "${sws_url}" | tar -xz -C /usr/local/bin --strip-components=1 static-web-server-v2.15.0-aarch64-unknown-linux-gnu/static-web-server
chmod +x /usr/local/bin/static-web-server
if [[ "$(command -v static-web-server)" != "/usr/local/bin/static-web-server" ]]; then
  log "static-web-server failed to install"
  exit 1
fi
