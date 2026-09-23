#!/bin/bash
# EC2 user data (Amazon Linux 2023). Paste it into Advanced details, User data.
# Installs Docker, the Compose v2 plugin and git, and lets ec2-user run docker
# without sudo. Output goes to /var/log/cloud-init-output.log
set -euxo pipefail

dnf update -y
dnf install -y docker git
systemctl enable --now docker

# AL2023 doesn't package compose v2, so get the plugin from GitHub
ARCH="$(uname -m)"   # x86_64 or aarch64
mkdir -p /usr/local/lib/docker/cli-plugins
curl -fsSL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-${ARCH}" \
  -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

# in a Session Manager shell run `sudo su - ec2-user` to use this user
usermod -aG docker ec2-user

docker version
docker compose version
echo "user-data finished" > /home/ec2-user/USER_DATA_DONE
