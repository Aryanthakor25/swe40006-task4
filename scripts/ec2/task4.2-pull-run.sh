#!/usr/bin/env bash
# SWE40006 Task 4.2: pull the image pushed from the laptop and run it on the
# EC2 instance (secondary Docker host).
#
# Usage:  bash task4.2-pull-run.sh <dockerhub-user> [tag] [host-port]
#   e.g.  bash task4.2-pull-run.sh aryanthakor 1.0 8080
# (8080 so it can stay up next to the Task 4.3 stack, which uses 80/443)
set -uo pipefail

HUB_USER="${1:?usage: $0 <dockerhub-user> [tag] [host-port]}"
TAG="${2:-1.0}"
PORT="${3:-8080}"
IMAGE="${HUB_USER}/swe40006-flask-app:${TAG}"
LOG="$HOME/task4.2-secondary-host.log"

D="docker"; $D info >/dev/null 2>&1 || D="sudo docker"

TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 60")
md() { curl -s -H "X-aws-ec2-metadata-token: $TOKEN" "http://169.254.169.254/latest/meta-data/$1"; }
PUBLIC_IP=$(md public-ipv4)

run() { echo; echo "\$ $*" | tee -a "$LOG"; "$@" 2>&1 | tee -a "$LOG"; }

{
  echo "=================================================================="
  echo " SWE40006 Task 4.2: secondary Docker host"
  echo " Student : Aryan Thakor (105061154)"
  echo " Host    : $(hostname)  instance=$(md instance-id)  type=$(md instance-type)"
  echo " Public  : ${PUBLIC_IP}"
  echo " Date    : $(date '+%Y-%m-%d %H:%M:%S %Z')"
  echo "=================================================================="
} | tee "$LOG"

run cat /etc/os-release
run $D version
run $D rm -f flask-app-4-2
run $D pull "$IMAGE"
run $D image ls "${HUB_USER}/swe40006-flask-app"
run $D run -d --name flask-app-4-2 --restart unless-stopped -p "${PORT}:5000" "$IMAGE"
sleep 3
run $D ps --filter name=flask-app-4-2
run curl -s "http://localhost:${PORT}/api/info"
run $D logs flask-app-4-2

echo
echo "Open http://${PUBLIC_IP}:${PORT}/ from your laptop (security group must allow TCP ${PORT})." | tee -a "$LOG"
echo "Log saved to $LOG"
