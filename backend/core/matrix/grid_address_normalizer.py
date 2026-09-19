"""지오코더 입력 주소 정규화 — store(SGIS 게이트웨이)·indicator(공공데이터 로더)가 같이 쓴다 (core는 apps를 import하지 않는다).

괄호 동명 제거, '지하' 제거(지하 주소를 엉뚱한 지점으로 돌려주는 실측, 2026-09-19), 원천 오타 교정.
"""

import re

_ADDRESS_FIXES = {"달구벌대호": "달구벌대로"}


def normalize_address(address: str) -> str:
    cleaned = re.sub(r"\(.*?\)", "", address)
    cleaned = re.sub(r"지하\s*", "", cleaned)
    for wrong, right in _ADDRESS_FIXES.items():
        cleaned = cleaned.replace(wrong, right)
    return re.sub(r"\s+", " ", cleaned).strip()
