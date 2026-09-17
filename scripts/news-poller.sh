#!/usr/bin/env bash
# 뉴스 폴링 수집기 크론 러너 — 매시 실행 (등록: crontab)
# 소스: 구글 뉴스 RSS (키 없음). 구·군 기본 키워드(인자 없음) + 대구 랜드마크 키워드 2회 실행
# 로그: logs/news-poller.log (마지막 2000줄 유지)
set -euo pipefail

BACKEND_DIR="/home/kimchungsik/projects/cloud.localhostdaegu/backend"
LOG_DIR="/home/kimchungsik/projects/cloud.localhostdaegu/logs"
LOG_FILE="${LOG_DIR}/news-poller.log"

mkdir -p "${LOG_DIR}"
cd "${BACKEND_DIR}"

{
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] news poller 시작"
  .venv/bin/python -m apps.news.adapter.inbound.cli.news_poller
  .venv/bin/python -m apps.news.adapter.inbound.cli.news_poller \
    "동성로 상권" "서문시장" "칠성시장" "대구 자영업" "대구 소상공인" "대구로 배달앱" \
    "iM뱅크 소상공인" "들안길 먹거리" "안지랑 곱창골목" "수성못 상권"
} >> "${LOG_FILE}" 2>&1 || { rc=$?; echo "[$(date '+%Y-%m-%d %H:%M:%S')] news poller 실패 (exit ${rc})" >> "${LOG_FILE}"; }

tail -n 2000 "${LOG_FILE}" > "${LOG_FILE}.tmp" && mv "${LOG_FILE}.tmp" "${LOG_FILE}"
