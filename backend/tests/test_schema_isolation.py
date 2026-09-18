"""고립 테이블 감시 — backend/CLAUDE.md §13 "어떤 테이블도 고립된 채로 존재할 수 없다".

규칙에는 **근거 있는 예외 2건**이 있다. 그 둘을 여기에 이름과 이유로 고정해,
새로 고립 테이블이 생기면(진짜 설계 오류) 이 테스트가 실패하게 한다.
산문으로만 적어 두면 다음 사람이 규칙을 어긴 줄 모르고 지나간다.
"""

import importlib
from pathlib import Path

from core.matrix.grid_oracle_database_manager import OrmBase

_APPS = Path(__file__).resolve().parents[1] / "apps"


def _register_all_orms() -> None:
    """apps/ 아래 모든 *_orm.py 를 import 해 메타데이터를 채운다.

    alembic env.py 의 등록 목록을 쓰지 않는다 — 거기에 빠진 ORM 이 있어도
    이 테스트는 잡아야 하기 때문이다.
    """
    for path in sorted(_APPS.rglob("*_orm.py")):
        module = ".".join(path.relative_to(_APPS.parent).with_suffix("").parts)
        importlib.import_module(module)

# 예외 — 왜 연결하지 않는지 여기에 적는다. 새 항목을 추가하려면 근거가 있어야 한다.
ALLOWED_ISOLATED = {
    "interest_rate": (
        "전국 단위 금리 시계열. 행정동·업종 어느 허브 키에도 함수 종속되지 않아 "
        "region 을 붙이면 144행정동 × 기간만큼 같은 값을 복제하게 되어 3NF 위반이다. "
        "계산기 유스케이스에서 rent_price 와 애플리케이션 조인한다."
    ),
    "funding_program": (
        "실질 참조는 rag_chunk.source_type='funding' + source_id 이지만 다형 참조라 FK 를 걸 수 없다. "
        "지역 M:N 을 만들어도 1,693건 중 자치구를 안전하게 붙일 수 있는 공고가 7건뿐이라(2026-09-18 실측) "
        "고립이 해소되지 않는다. 대구 시 단위 50건은 자치구가 아니라 행정동 허브에 붙지 않는다."
    ),
}


def _isolated_tables() -> set[str]:
    _register_all_orms()
    metadata = OrmBase.metadata
    referenced = {fk.column.table.name for table in metadata.tables.values() for fk in table.foreign_keys}
    has_outgoing = {name for name, table in metadata.tables.items() if table.foreign_keys}
    return {name for name in metadata.tables if name not in referenced and name not in has_outgoing}


def test_no_new_isolated_tables():
    unexpected = _isolated_tables() - set(ALLOWED_ISOLATED)

    assert unexpected == set(), (
        f"고립 테이블이 새로 생겼다(§13 위반): {sorted(unexpected)}. "
        "허브에 엣지를 잇거나, 잇지 않는 근거를 ALLOWED_ISOLATED 에 적는다."
    )


def test_allowlist_has_no_stale_entries():
    """예외가 해소됐는데 목록에 남아 있으면 규칙이 느슨해진다."""
    resolved = set(ALLOWED_ISOLATED) - _isolated_tables()

    assert resolved == set(), f"이제 연결된 테이블이 예외 목록에 남아 있다: {sorted(resolved)}"


def test_every_exception_states_a_reason():
    for table, reason in ALLOWED_ISOLATED.items():
        assert len(reason) > 40, f"{table} 의 예외 근거가 너무 짧다"
