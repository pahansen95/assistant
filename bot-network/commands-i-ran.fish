#!/usr/bin/env fish
echo "Don't run me. Demonstration Purposes only." >&2
exit 1

alias --save kubectl 'sudo k3s kubectl'

# Build the containers
sudo podman build \
  --tag='headscale-app:v0.21.0_2023.01.30-beta-1' \
  --file='container/Dockerfile' \
  "$HOME/headscale/"

sudo podman save "headscale-app:v0.21.0_2023.01.30-beta-1" |
  sudo k3s ctr images import -

# Run the App
kubectl apply -f "$HOME/headscale/k8s-app.yaml"

# Headscale Admin Tool
alias --save headscale 'kubectl exec -it deployments/headscale -c=headscale-mgmt-server -- headscale'

# Get Instructions for connecting to your Headscale Network on MacOS/IOS
curl -fsSL https://vpn.assistant-dev.peterhansen.io/apple

# Start Tailscale on Linux
sudo tailscale up \
  --login-server https://vpn.assistant-dev.peterhansen.io \
  --accept-routes \
  --reset --force-reauth \
  --accept-risk all \
  --authkey=...

# Generate a Synapse Files
podman run --rm -it \
  --env UID=$(id -u) --env GID=$(id -g) \
  --env SYNAPSE_SERVER_NAME=assistant-dev \
  --env SYNAPSE_REPORT_STATS=yes \
  --mount "type=bind,source=$PWD,destination=/data" \
  ghcr.io/matrix-org/synapse:v1.81.0 \
    generate

# Synapse Admin Tool
alias --save matrix-cli 'kubectl exec -it deployments/matrix -c=matrix-api -- bash'

# Bootstrap the Matrix Environment
matrix-cli
# The rest of these commands are run inside the container

register_new_matrix_user \
  --user=admin \
  --admin \
  --config=/etc/synapse/config.yaml

register_new_matrix_user \
  --user=peter \
  --no-admin \
  --config=/etc/synapse/config.yaml \

register_new_matrix_user \
  --user=assistant \
  --no-admin \
  --config=/etc/synapse/config.yaml

# Exit the container