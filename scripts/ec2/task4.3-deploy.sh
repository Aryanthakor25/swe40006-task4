#!/usr/bin/env bash
# SWE40006 Task 4.3: deploy the StudyPulse stack on EC2.
# Pulls the web image from Docker Hub (nothing is built on the server) plus redis,
# and caddy for HTTPS on a free sslip.io hostname when --https is given.
#
# Run from the repo root after cloning it on the instance:
#   git clone https://github.com/Aryanthakor25/swe40006-task4.git && cd swe40006-task4
#   bash scripts/ec2/task4.3-deploy.sh <dockerhub-user>            # HTTP on port 80
#   bash scripts/ec2/task4.3-deploy.sh <dockerhub-user> --https    # HTTPS on 443 (+80 redirect)
set -uo pipefail

HUB_USER="${1:?usage: $0 <dockerhub-user> [--https]}"
MODE="${2:-}"
VERSION="${APP_VERSION:-1.0.0}"
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
APP_DIR="$REPO_ROOT/task4.3-studypulse"
LOG="$HOME/task4.3-ec2-deploy.log"

D="docker"; $D info >/dev/null 2>&1 || D="sudo docker"

TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 60")
md() { curl -s -H "X-aws-ec2-metadata-token: $TOKEN" "http://169.254.169.254/latest/meta-data/$1"; }
PUBLIC_IP=$(md public-ipv4)
DOMAIN="${PUBLIC_IP//./-}.sslip.io"

run() { echo; echo "\$ $*" | tee -a "$LOG"; "$@" 2>&1 | tee -a "$LOG"; }

if [[ "$MODE" == "--https" ]]; then
  HOST_PORT=8000; PROFILE=(--profile https); URL="https://${DOMAIN}"
else
  HOST_PORT=80;   PROFILE=();                URL="http://${PUBLIC_IP}"
fi

cd "$APP_DIR" || exit 1
cat > .env <<EOF
DOCKERHUB_USER=${HUB_USER}
APP_VERSION=${VERSION}
APP_TITLE=StudyPulse
APP_ENV=production
LOG_LEVEL=info
REDIS_HOST=redis
REDIS_PORT=6379
HOST_PORT=${HOST_PORT}
DOMAIN=${DOMAIN}
EOF

{
  echo "=================================================================="
  echo " SWE40006 Task 4.3: EC2 deployment ($([[ -n "$MODE" ]] && echo HTTPS || echo HTTP))"
  echo " Student : Aryan Thakor (105061154)"
  echo " Host    : $(hostname)  instance=$(md instance-id)  type=$(md instance-type)"
  echo " Public  : ${PUBLIC_IP}   domain=${DOMAIN}"
  echo " Date    : $(date '+%Y-%m-%d %H:%M:%S %Z')"
  echo "=================================================================="
} | tee "$LOG"

run cat .env
run $D compose "${PROFILE[@]}" pull
run $D compose "${PROFILE[@]}" up -d --no-build
echo "waiting 20s for health checks (and the TLS certificate if --https)..."
sleep 20
run $D compose "${PROFILE[@]}" ps
run $D network ls --filter name=studypulse
run curl -s "http://localhost:${HOST_PORT}/health"
run curl -s "http://localhost:${HOST_PORT}/api/info"
if [[ "$MODE" == "--https" ]]; then
  run curl -sI "http://${DOMAIN}"             # expect 308 redirect to https
  run curl -s "https://${DOMAIN}/health"
  run $D compose logs --tail 20 caddy
fi
run $D compose logs --tail 20 web

echo
echo "Public URL for the report / live grading:  ${URL}" | tee -a "$LOG"
echo "Security group needs inbound TCP 80$([[ -n "$MODE" ]] && echo ' and 443') from 0.0.0.0/0." | tee -a "$LOG"
echo "Log saved to $LOG"
