#!/usr/bin/env bash
# RAG 증분 색인 크론 러너 — 매일 16:10 실행 (등록: crontab)
# Gemini 무료 등급은 임베딩 요청 일 1,000건(배치 내 문서 단위로 계산) — 태평양 자정(KST 16:00) 리셋 직후 실행.
# 증분 색인을 60초 간격으로 반복하다가 "0건 처리"(완료) 또는 6회 연속 정체(일 한도 소진)면 멈춘다.
# 로그: logs/rag-indexer.log (마지막 2000줄 유지)
set -euo pipefail

BACKEND_DIR="/home/kimchungsik/projects/cloud.localhostdaegu/backend"
LOG_DIR="/home/kimchungsik/projects/cloud.localhostdaegu/logs"
LOG_FILE="${LOG_DIR}/rag-indexer.log"

mkdir -p "${LOG_DIR}"
cd "${BACKEND_DIR}"

count_chunks() {
  .venv/bin/python -c "
from sqlalchemy import text
from core.matrix.grid_oracle_database_manager import session_scope
with session_scope() as s: print(s.execute(text('select count(*) from rag_chunk')).scalar())"
}

{
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] rag indexer 시작 (provider=gemini)"
  prev=""
  stall=0
  for i in $(seq 1 40); do
    log=$(timeout 300 .venv/bin/python -m apps.rag.adapter.inbound.cli.build_rag_index --provider gemini 2>&1 || true)
    line=$(echo "$log" | grep -E "^rag indexer:" | tail -1)
    [ -z "$line" ] && line="429 중단 (증분 계속)"
    cnt=$(count_chunks)
    echo "[$(date '+%H:%M:%S')] run $i | rag_chunk=$cnt | $line"
    if echo "$line" | grep -qE "색인 0건 처리"; then echo "완료: 신규 청크 없음 (총 $cnt)"; break; fi
    if [ "$cnt" = "$prev" ]; then stall=$((stall + 1)); else stall=0; fi
    if [ "$stall" -ge 5 ]; then echo "정체: 일 한도 소진으로 판단, 중단 (총 $cnt)"; break; fi
    prev=$cnt
    sleep 60
  done
} >> "${LOG_FILE}" 2>&1 || { rc=$?; echo "[$(date '+%Y-%m-%d %H:%M:%S')] rag indexer 실패 (exit ${rc})" >> "${LOG_FILE}"; }

tail -n 2000 "${LOG_FILE}" > "${LOG_FILE}.tmp" && mv "${LOG_FILE}.tmp" "${LOG_FILE}"
