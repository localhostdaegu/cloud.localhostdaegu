#!/usr/bin/env bash
# 한국은행 기준금리·대출금리 + R-ONE 임대동향 수집기 크론 러너 — 주 1회(월 05:20) 실행 (등록: crontab)
# ECOS 722Y001 월별 기준금리 → interest_rate 업서트(멱등)
# ECOS 121Y006 가중평균 대출금리(신규취급액, 3계열) → interest_rate 업서트(멱등) — 월 공표라 주 1회로 충분
# R-ONE 임대료·공실률(분기, 통계표 20개, 대구 필터) → rent_price 업서트(멱등) — 분기 공표라 주 1회로 충분
set -euo pipefail

BACKEND_DIR="/home/kimchungsik/projects/cloud.localhostdaegu/backend"
LOG_DIR="/home/kimchungsik/projects/cloud.localhostdaegu/logs"
LOG_FILE="${LOG_DIR}/interest-rate-collector.log"

source "$(dirname "${BASH_SOURCE[0]}")/_lib.sh"
cron_begin "interest/rent collector" "${LOG_FILE}"
cd "${BACKEND_DIR}"

step "interest rate collector" .venv/bin/python -m apps.shock.adapter.inbound.cli.load_interest_rate
step "loan rate collector" .venv/bin/python -m apps.shock.adapter.inbound.cli.load_loan_rate
step "rent price collector" .venv/bin/python -m apps.rent.adapter.inbound.cli.load_rent_price

cron_end 2000
