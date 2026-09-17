"""/analysis API — POST 시작 → GET SSE 가 프론트 EventSource 계약대로 나오는지 (Fake 포트)."""

import json

from fastapi.testclient import TestClient

from apps.analysis.dependencies.analysis_dependencies import get_analysis_use_case
from main import app
from tests.analysis_fakes import FINANCE, build_interactor


def _client() -> TestClient:
    interactor = build_interactor()  # POST·GET 이 같은 저장소를 공유해야 한다
    app.dependency_overrides[get_analysis_use_case] = lambda: interactor
    return TestClient(app)


def teardown_function() -> None:
    app.dependency_overrides.clear()


def _parse_sse(text: str) -> list[tuple[str, dict]]:
    events = []
    for block in text.split("\n\n"):
        if not block.strip():
            continue
        lines = dict(line.split(": ", 1) for line in block.split("\n"))
        events.append((lines["event"], json.loads(lines["data"])))
    return events


def test_myself_is_wired():
    assert TestClient(app).get("/analysis/myself").json() == {"app": "analysis", "status": "wired"}


def test_post_returns_analysis_id():
    response = _client().post("/analysis", json={"region": "2711059500", "industry": "cafe"})
    assert response.status_code == 200
    assert len(response.json()["analysis_id"]) == 32


def test_events_stream_follows_frontend_eventsource_contract():
    client = _client()
    analysis_id = client.post(
        "/analysis", json={"region": "2711059500", "industry": "cafe", "question": "원두값 오르면?"}
    ).json()["analysis_id"]

    response = client.get(f"/analysis/{analysis_id}/events")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["cache-control"] == "no-cache"
    assert "content-encoding" not in response.headers  # GZip 미들웨어가 스트림을 압축하지 않아야 한다
    events = _parse_sse(response.text)
    assert all(name == data["type"] for name, data in events)
    assert events[0] == ("agent_status", {"type": "agent_status", "agent": "orchestrator", "status": "running"})
    assert events[-1][0] == "report_done"
    assert events[-1][1]["report_id"] == analysis_id
    sections = [data["section"] for name, data in events if name == "report_delta"]
    assert sections[0] == "verdict"
    assert "calculator" not in sections


def test_finance_body_adds_calculator_section():
    client = _client()
    analysis_id = client.post(
        "/analysis", json={"region": "2711059500", "industry": "cafe", "finance": FINANCE}
    ).json()["analysis_id"]

    events = _parse_sse(client.get(f"/analysis/{analysis_id}/events").text)

    assert "calculator" in [data["section"] for name, data in events if name == "report_delta"]


def test_events_404_for_unknown_or_consumed_id():
    client = _client()
    analysis_id = client.post("/analysis", json={"region": "2711059500", "industry": "cafe"}).json()["analysis_id"]
    client.get(f"/analysis/{analysis_id}/events")

    for target in ("nope", analysis_id):
        response = client.get(f"/analysis/{target}/events")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "ANALYSIS_NOT_FOUND"


def test_post_rejects_missing_industry():
    assert _client().post("/analysis", json={"region": "2711059500"}).status_code == 422


def test_post_rejects_overlong_question():
    body = {"region": "2711059500", "industry": "cafe", "question": "가" * 501}
    assert _client().post("/analysis", json=body).status_code == 422
