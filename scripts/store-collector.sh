#!/usr/bin/env bash
# 인허가 점포 증분 수집기 크론 러너 — 매일 04:20 실행 (등록: crontab)
# DB의 (업종×구·군) 최근 갱신시점 커서 기준 증분만 수집 (DAT_UPDT_PNT::GTE)
# 대구: store → geocode_stores(캐시) → assign_regions → build_metrics 4단 (학원·부동산 재수집은 수동, docs/handoff.md)
set -euo pipefail

BACKEND_DIR="/home/kimchungsik/projects/cloud.localhostdaegu/backend"
LOG_DIR="/home/kimchungsik/projects/cloud.localhostdaegu/logs"
LOG_FILE="${LOG_DIR}/store-collector.log"

source "$(dirname "${BASH_SOURCE[0]}")/_lib.sh"
cron_begin "store collector" "${LOG_FILE}"
cd "${BACKEND_DIR}"

step "store collector" .venv/bin/python -m apps.store.adapter.inbound.cli.store_collector
# 증분 업서트(merge)가 원천 좌표 없는 행의 lat/lng를 비우므로 캐시에서 복원 (신규 주소만 SGIS 호출)
step "SGIS 지오코딩 (좌표 없는 인허가·학원·부동산, 캐시 우선)" .venv/bin/python -m apps.store.adapter.inbound.cli.geocode_stores
step "region 공간조인 (신규분)" .venv/bin/python -m apps.store.adapter.inbound.cli.assign_regions
step "지표 배치 집계 (region_industry_metric)" .venv/bin/python -m apps.metric.adapter.inbound.cli.build_metrics

cron_end 5000
