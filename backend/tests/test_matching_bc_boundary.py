"""matching BC 경계 — backend/CLAUDE.md §7·§11.

§7: "Business logic imports Ports, never Adapters."
§11: BC 완전 분리. 다른 BC 접근은 어댑터 레이어에서 그 BC의 **유스케이스**를 주입받는 형태로만 한다
     (좋은 예: apps/analysis 의 market_data_gateway).
"""

import ast
from pathlib import Path

_MATCHING = Path(__file__).resolve().parents[1] / "apps" / "matching"


def _imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text())
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            modules.append(node.module)
        elif isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
    return modules


def _all_imports() -> dict[Path, list[str]]:
    return {path: _imports(path) for path in _MATCHING.rglob("*.py")}


def test_matching_never_imports_another_bc_adapter():
    """다른 BC 의 Adapter(리포지토리·ORM 구현)를 직접 쓰지 않는다."""
    offenders = {
        str(path.relative_to(_MATCHING)): [
            m for m in modules
            if m.startswith("apps.") and ".adapter." in m and not m.startswith("apps.matching.")
        ]
        for path, modules in _all_imports().items()
    }
    offenders = {k: v for k, v in offenders.items() if v}

    assert offenders == {}, f"다른 BC 어댑터 직접 import: {offenders}"


def test_matching_domain_stays_free_of_other_bcs():
    """도메인은 어느 BC 도 모른다 — dict 만 본다."""
    for path, modules in _all_imports().items():
        if "domain" not in path.parts:
            continue
        foreign = [m for m in modules if m.startswith("apps.") and not m.startswith("apps.matching.")]
        assert foreign == [], f"{path.name} 이 다른 BC 를 import 한다: {foreign}"
