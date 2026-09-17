#!/usr/bin/env bash
# 크론 러너 공통 헬퍼 — source 해서 쓴다.
#   cron_begin <이름> <로그파일>  : 로그로 출력 전환 + flock 중복 실행 방지(실행 중이면 건너뜀)
#   step <단계명> <명령…>          : 단계별 종료코드 기록, 실패해도 다음 단계 계속, 최악 코드 유지
#   cron_end <유지 줄 수>          : 최종 결과 줄 기록 → 로그 줄 수 정리 → 최악 코드로 종료
# `{ … } >> log || …` 형태는 좌변 그룹 안에서 set -e 가 무시돼 마지막 단계 실패만 보고됐다 (2026-09-18 리뷰).

CRON_NAME=""
CRON_LOG=""
WORST_RC=0

_ts() { date '+%Y-%m-%d %H:%M:%S'; }

cron_begin() {
  CRON_NAME="$1"
  CRON_LOG="$2"
  mkdir -p "$(dirname "${CRON_LOG}")"
  exec >> "${CRON_LOG}" 2>&1
  exec 9> "${CRON_LOG%.log}.lock"
  if ! flock -n 9; then
    echo "[$(_ts)] ${CRON_NAME} 이전 실행이 아직 진행 중 — 이번 실행 건너뜀"
    exit 0
  fi
  echo "[$(_ts)] ${CRON_NAME} 크론 시작"
}

step() {
  local name="$1"
  shift
  local rc=0
  echo "[$(_ts)] ${name} 시작"
  "$@" || rc=$?
  echo "[$(_ts)] ${name} 종료 (exit ${rc})"
  if [ "${rc}" -gt "${WORST_RC}" ]; then
    WORST_RC="${rc}"
  fi
  return 0
}

cron_end() {
  local keep_lines="$1"
  if [ "${WORST_RC}" -eq 0 ]; then
    echo "[$(_ts)] ${CRON_NAME} 크론 완료 (exit 0)"
  else
    echo "[$(_ts)] ${CRON_NAME} 크론 실패 — 최악 종료코드 ${WORST_RC}"
  fi
  tail -n "${keep_lines}" "${CRON_LOG}" > "${CRON_LOG}.tmp" && mv "${CRON_LOG}.tmp" "${CRON_LOG}"
  exit "${WORST_RC}"
}
