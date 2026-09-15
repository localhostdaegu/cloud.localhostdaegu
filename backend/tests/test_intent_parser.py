from apps.intent.domain.parser import parse_intent

# 사전은 순수 함수 인자 — DB 없이 테스트
DONGS = {"대신동": "27110", "상동": "27260", "중동": "27260", "성내1동": "27110"}
GUS = {"중구": "27110", "수성구": "27260", "달서구": "27290"}

def test_type_a_full():
    r = parse_intent("수성구 들안길에 카페 차리고 싶어, 예산 5천", DONGS, GUS)
    assert r.intent_type == "A"
    assert r.district_code == "27260"           # 들안길 → 랜드마크 별칭 → 수성구
    assert r.industry_slug == "rest_cafes"      # 카페 → 휴게음식점
    assert r.budget_krw == 50_000_000           # "5천" → 5,000만원

def test_type_b_region_only():
    r = parse_intent("서문시장 근처에서 장사하고 싶은데", DONGS, GUS)
    assert r.intent_type == "B"
    assert r.district_code == "27110"           # 서문시장 → 대신동 → 중구
    assert "industry" in r.missing

def test_type_c_budget_only():
    r = parse_intent("예산 5천이면 뭐 할 수 있어?", DONGS, GUS)
    assert r.intent_type == "C"
    assert r.budget_krw == 50_000_000
    assert "region" in r.missing

def test_budget_variants():
    assert parse_intent("3억으로", DONGS, GUS).budget_krw == 300_000_000
    assert parse_intent("7000만원 있어", DONGS, GUS).budget_krw == 70_000_000
