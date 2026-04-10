# 이 파일은 Planner 결과 payload의 파싱/검증 동작을 단위 테스트한다.
# 외부 LLM 호출 없이 fixture JSON만으로 계획 구조 안정성을 검증한다.
# query_type, step 순서, depends_on 규칙이 유지되는지 빠르게 확인할 수 있다.
# 리팩터링 이후에도 Planner 데이터 계약이 깨지지 않도록 회귀 방지 역할을 한다.

from __future__ import annotations

import json
from pathlib import Path

from Planner.models import PlannerPlan
from Planner.plan_validator import validate_plan_payload


def test_parse_db_then_rag_plan_fixture(fixture_root: Path) -> None:
    """
    DB_THEN_RAG fixture가 검증/파싱 가능한지 확인한다.

    Args:
        fixture_root: fixture 루트 경로.
    """
    payload = json.loads((fixture_root / "planner" / "sample_plan_db_then_rag.json").read_text(encoding="utf-8"))
    validate_plan_payload(payload)
    plan = PlannerPlan.from_dict(payload)

    assert plan.query_type == "DB_THEN_RAG"
    assert len(plan.steps) == 2
    assert plan.steps[1].depends_on == [1]


def test_parse_db_only_plan_fixture(fixture_root: Path) -> None:
    """
    DB_ONLY fixture가 단일 step 구조를 유지하는지 확인한다.

    Args:
        fixture_root: fixture 루트 경로.
    """
    payload = json.loads((fixture_root / "planner" / "sample_plan_db_only.json").read_text(encoding="utf-8"))
    validate_plan_payload(payload)
    plan = PlannerPlan.from_dict(payload)

    assert plan.query_type == "DB_ONLY"
    assert len(plan.steps) == 1
    assert plan.steps[0].type == "db"

