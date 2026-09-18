"""consultation DB 왕복 — POST /consultation → PUT .../plans/current → GET /consultation/{id}.

**이 파일은 alembic 리비전(작업 D)이 올라오기 전까지 실패한다** — consultation_* 4테이블이
아직 테스트 DB에 없다. 순수 로직 테스트(test_consultation_interactor·_mappers)는 D와 무관하게 통과한다.
"""

from fastapi.testclient import TestClient

from main import app

_PLAN_INPUT = {
    "deposit": 30_000_000,
    "key_money": 10_000_000,
    "interior_cost": 40_000_000,
    "equipment_cost": 20_000_000,
    "monthly_rent": 1_800_000,
    "monthly_payroll": 3_000_000,
    "monthly_insurance": 200_000,
    "cost_ratio": 0.35,
    "fee_ratio": 0.05,
    "equity": 60_000_000,
    "desired_loan": 50_000_000,
    "loan_rate": 0.045,
    "expected_monthly_revenue": 18_000_000,
}


def _create_session(client: TestClient, **profile) -> str:
    response = client.post("/consultation", json=profile)
    assert response.status_code == 201, response.text
    return response.json()["session_id"]


def test_create_save_plan_and_get_round_trip():
    client = TestClient(app)
    session_id = _create_session(client, region_code="2711059500", industry_id="cafe")

    saved = client.put(f"/consultation/{session_id}/plans/current", json=_PLAN_INPUT)
    assert saved.status_code == 200, saved.text

    detail = client.get(f"/consultation/{session_id}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["session"]["region_code"] == "2711059500"
    assert len(body["plans"]) == 1
    assert body["plans"][0]["plan_kind"] == "current"
    assert body["plans"][0]["monthly_rent"] == 1_800_000


def test_saving_same_plan_kind_twice_updates_without_unique_violation():
    client = TestClient(app)
    session_id = _create_session(client)

    first = client.put(f"/consultation/{session_id}/plans/current", json=_PLAN_INPUT)
    second = client.put(
        f"/consultation/{session_id}/plans/current",
        json={**_PLAN_INPUT, "monthly_rent": 2_500_000},
    )

    assert second.status_code == 200, second.text
    assert second.json()["plan_id"] == first.json()["plan_id"]
    plans = client.get(f"/consultation/{session_id}").json()["plans"]
    assert len(plans) == 1
    assert plans[0]["monthly_rent"] == 2_500_000


def test_baseline_and_current_coexist():
    client = TestClient(app)
    session_id = _create_session(client)

    client.put(f"/consultation/{session_id}/plans/baseline", json=_PLAN_INPUT)
    client.put(f"/consultation/{session_id}/plans/current", json=_PLAN_INPUT)

    kinds = [p["plan_kind"] for p in client.get(f"/consultation/{session_id}").json()["plans"]]
    assert kinds == ["baseline", "current"]


def test_unknown_profile_survives_db_round_trip_as_null():
    """인수 기준 — business_registered·owner_age 미입력이 False·0이 아니라 None으로 왕복한다."""
    client = TestClient(app)
    session_id = _create_session(client)

    session = client.get(f"/consultation/{session_id}").json()["session"]

    assert session["business_registered"] is None
    assert session["owner_age"] is None
    assert session["business_age_months"] is None


def test_invalid_plan_kind_returns_400():
    client = TestClient(app)
    session_id = _create_session(client)

    response = client.put(f"/consultation/{session_id}/plans/selected", json=_PLAN_INPUT)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_PLAN_KIND"


def test_unknown_session_returns_404():
    client = TestClient(app)

    assert client.get("/consultation/0123456789abcdef").status_code == 404
    put = client.put("/consultation/0123456789abcdef/plans/current", json=_PLAN_INPUT)
    assert put.status_code == 404
    assert put.json()["error"]["code"] == "SESSION_NOT_FOUND"

def test_notes_are_saved_with_the_session():
    """§5-1 — '모름'을 선택한 사실이 가정으로 바뀌며 사라지지 않게 세션에 남긴다.

    쓰기 경로가 없으면 consultation_note 는 영원히 빈 테이블이다.
    """
    client = TestClient(app)
    session_id = _create_session(
        client,
        region_code="2711059500",
        industry_id="cafe",
        assumptions=["원가율 57%는 업종 벤치마크 기본값", "대출금리 연 4.8% 가정"],
        open_questions=["설비 견적 미확정", "보증기관 보증서 진행 상태 미확인"],
    )

    notes = client.get(f"/consultation/{session_id}").json()["notes"]

    assert [(n["note_type"], n["note_order"], n["content"]) for n in notes] == [
        ("assumption", 1, "원가율 57%는 업종 벤치마크 기본값"),
        ("assumption", 2, "대출금리 연 4.8% 가정"),
        ("open_question", 1, "설비 견적 미확정"),
        ("open_question", 2, "보증기관 보증서 진행 상태 미확인"),
    ]


def test_session_without_notes_stays_empty():
    """노트가 비어 있다는 사실을 '확인 완료'로 읽지 않는다 — 안 보낸 것과 없는 것은 같다."""
    client = TestClient(app)
    session_id = _create_session(client, region_code="2711059500", industry_id="cafe")

    assert client.get(f"/consultation/{session_id}").json()["notes"] == []


def test_saving_a_document_records_hash_and_links_the_plan():
    """상담자료를 저장하면 어떤 선택안으로 만든 자료인지 함께 남는다.
    content_hash 는 내용 변경 확인용이며 블록체인 앵커링이 아니다."""
    import hashlib

    client = TestClient(app)
    session_id = _create_session(client, region_code="2711059500", industry_id="cafe")
    client.put(f"/consultation/{session_id}/plans/current", json=_PLAN_INPUT)

    markdown = "# 창업자금 상담 준비자료\n\n총 준비자금 62,600,000원\n"
    saved = client.post(
        f"/consultation/{session_id}/documents",
        json={"plan_kind": "current", "purpose": "handoff", "content_markdown": markdown},
    )

    assert saved.status_code == 201, saved.text
    body = saved.json()
    assert body["content_hash"] == hashlib.sha256(markdown.encode()).hexdigest()
    assert body["purpose"] == "handoff"
    assert body["plan_id"]


def test_document_for_a_missing_plan_is_rejected():
    client = TestClient(app)
    session_id = _create_session(client, region_code="2711059500", industry_id="cafe")

    response = client.post(
        f"/consultation/{session_id}/documents",
        json={"plan_kind": "baseline", "purpose": "handoff", "content_markdown": "x"},
    )

    assert response.status_code == 404


def test_document_for_a_missing_session_is_rejected():
    response = TestClient(app).post(
        "/consultation/deadbeef/documents",
        json={"plan_kind": "current", "purpose": "handoff", "content_markdown": "x"},
    )

    assert response.status_code == 404


def test_updating_a_session_replaces_state_without_creating_a_new_one():
    """선택안을 바꿔 다시 상담자료를 만들어도 세션이 쌓이지 않는다.

    부분 병합이 아니라 **교체**다 — 클라이언트가 늘 전체 초안을 들고 있기 때문이다.
    """
    client = TestClient(app)
    session_id = _create_session(
        client,
        region_code="2711059500",
        industry_id="cafe",
        selected_plan_kind="baseline",
        change_reason="처음 계획",
        open_questions=["설비 견적 미확정"],
    )

    updated = client.put(
        f"/consultation/{session_id}",
        json={
            "region_code": "2711059500",
            "industry_id": "cafe",
            "selected_plan_kind": "current",
            "change_reason": "월세가 낮은 자리로 바꿨습니다",
            "open_questions": ["보증기관 보증서 진행 상태 미확인"],
        },
    )
    assert updated.status_code == 200, updated.text

    body = client.get(f"/consultation/{session_id}").json()
    assert body["session"]["selected_plan_kind"] == "current"
    assert body["session"]["change_reason"] == "월세가 낮은 자리로 바꿨습니다"
    assert [n["content"] for n in body["notes"]] == ["보증기관 보증서 진행 상태 미확인"]


def test_updating_a_missing_session_is_rejected():
    response = TestClient(app).put("/consultation/deadbeef", json={"industry_id": "cafe"})

    assert response.status_code == 404
