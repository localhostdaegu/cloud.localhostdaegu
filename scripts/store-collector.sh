#!/usr/bin/env bash
# 인허가 점포 증분 수집기 크론 러너 — 매일 04:20 실행 (등록: crontab)
# DB의 (업종×구·군) 최근 갱신시점 커서 기준 증분만 수집 (DAT_UPDT_PNT::GTE)
# 대구: store → assign_regions → build_metrics 3단 (서울 전용 academy·broker 단계 없음)
set -euo pipefail

BACKEND_DIR="/home/kimchungsik/projects/cloud.localhostdaegu/backend"
LOG_DIR="/home/kimchungsik/projects/cloud.localhostdaegu/logs"
LOG_FILE="${LOG_DIR}/store-collector.log"

source "$(dirname "${BASH_SOURCE[0]}")/_lib.sh"
cron_begin "store collector" "${LOG_FILE}"
cd "${BACKEND_DIR}"

step "store collector" .venv/bin/python -m apps.store.adapter.inbound.cli.store_collector
step "region 공간조인 (신규분)" .venv/bin/python -m apps.store.adapter.inbound.cli.assign_regions
step "지표 배치 집계 (region_industry_metric)" .venv/bin/python -m apps.metric.adapter.inbound.cli.build_metrics

cron_end 5000
