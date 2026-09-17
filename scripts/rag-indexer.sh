#!/usr/bin/env bash
# RAG 증분 색인 크론 러너 — 매일 05:30 실행 (등록: crontab). store 04:20·funding 05:10 수집 직후
# Gemini 유료 키(2026-09-17 교체) 기준 1회 실행으로 전량 처리(1,595청크 69초 실측).
# 증분 색인을 60초 간격으로 반복하다가 "0건 처리"(완료) 또는 6회 연속 정체(429 지속)면 멈춘다.
# 완료 못 하고 멈추면(정체·반복 소진) 실패로 보고한다.
# 로그: logs/rag-indexer.log (마지막 2000줄 유지)
set -euo pipefail

BACKEND_DIR="/home/kimchungsik/projects/cloud.localhostdaegu/backend"
LOG_DIR="/home/kimchungsik/projects/cloud.localhostdaegu/logs"
LOG_FILE="${LOG_DIR}/rag-indexer.log"

source "$(dirname "${BASH_SOURCE[0]}")/_lib.sh"
cron_begin "rag indexer (provider=gemini)" "${LOG_FILE}"
cd "${BACKEND_DIR}"

count_chunks() {
  .venv/bin/python -c "
from sqlalchemy import text
from core.matrix.grid_oracle_database_manager import session_scope
with session_scope() as s: print(s.execute(text('select count(*) from rag_chunk')).scalar())"
}

index_until_done() {
  local prev="" stall=0 i log line cnt run_rc
  for i in $(seq 1 40); do
    run_rc=0
    log=$(timeout 300 .venv/bin/python -m apps.rag.adapter.inbound.cli.build_rag_index --provider gemini 2>&1) || run_rc=$?
    line=$(echo "$log" | grep -E "^rag indexer:" | tail -1 || true)
    cnt=$(count_chunks)
    if [ -z "$line" ]; then
      # 상태 줄이 없으면 원인을 단정하지 않고(429 외 오류 가능) 출력 끝부분을 남긴다
      echo "[$(date '+%H:%M:%S')] run $i | rag_chunk=$cnt | 상태 줄 없음 (exit ${run_rc}) — 출력 마지막 20줄:"
      echo "$log" | tail -n 20 | sed 's/^/    /'
    else
      echo "[$(date '+%H:%M:%S')] run $i | rag_chunk=$cnt | $line"
    fi
    if echo "$line" | grep -qE "색인 0건 처리"; then echo "완료: 신규 청크 없음 (총 $cnt)"; return 0; fi
    if [ "$cnt" = "$prev" ]; then stall=$((stall + 1)); else stall=0; fi
    if [ "$stall" -ge 5 ]; then echo "정체: 일 한도 소진으로 판단, 중단 (총 $cnt)"; return 1; fi
    prev=$cnt
    sleep 60
  done
  echo "반복 40회 소진: 완료 확인 못 함 (총 $cnt)"
  return 1
}

step "rag 증분 색인 반복" index_until_done

cron_end 2000
