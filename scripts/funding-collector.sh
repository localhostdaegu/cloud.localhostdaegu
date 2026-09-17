#!/usr/bin/env bash
# 정책자금 공고 수집기 크론 러너 — 매일 05:10 실행 (등록: crontab)
# 기업마당 API 1회 호출 전량 수신 → 업서트(멱등) → 만료 갱신
set -euo pipefail

BACKEND_DIR="/home/kimchungsik/projects/cloud.localhostdaegu/backend"
LOG_DIR="/home/kimchungsik/projects/cloud.localhostdaegu/logs"
LOG_FILE="${LOG_DIR}/funding-collector.log"

source "$(dirname "${BASH_SOURCE[0]}")/_lib.sh"
cron_begin "funding collector" "${LOG_FILE}"
cd "${BACKEND_DIR}"

step "funding collector" .venv/bin/python -m apps.funding.adapter.inbound.cli.funding_collector

cron_end 2000
