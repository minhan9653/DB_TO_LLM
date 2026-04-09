# 이 파일은 Planner 단계의 실제 LLM 호출 기반 동작을 검증하는 테스트다.
# mock 없이 PlannerService를 직접 호출해 JSON 계획의 최소 구조를 확인한다.
# 문자열 전체 일치 대신 query_type, step 순서, depends_on 규칙 중심으로 검증한다.
# 테스트 목적은 Planner 분류 품질 회귀를 빠르게 감지하는 것이다.

from __future__ import annotations

from pathlib import Path

from Planner.models import PlannerPlan
from Planner.planner_service import PlannerService

CONFIG_PATH = Path(__file__).resolve().parents[2] / "Root_Stream" / "config" / "config.yaml"


def _assert_common_plan_shape(plan: PlannerPlan) -> None:
    """
    모든 테스트 케이스에서 공통으로 확인할 최소 형식을 검증한다.
    """
    assert isinstance(plan.is_composite, bool)
    assert isinstance(plan.query_type, str) and plan.query_type
    assert len(plan.steps) >= 1

    expected_step_number = 1
    for step in plan.steps:
        assert step.step == expected_step_number
        assert step.type in {"db", "rag", "general"}
        assert isinstance(step.goal, str) and step.goal.strip()
        assert isinstance(step.depends_on, list)
        expected_step_number += 1


def _assert_step_sequence(plan: PlannerPlan, expected_types: list[str], expected_depends_on: list[list[int]]) -> None:
    """
    step.type 순서와 depends_on 참조를 비교한다.
    """
    assert len(plan.steps) == len(expected_types)
    assert [step.type for step in plan.steps] == expected_types
    assert [step.depends_on for step in plan.steps] == expected_depends_on


def test_planner_db_only_live() -> None:
    """
    정형 데이터 집계 질문에서 DB_ONLY + 단일 db step을 기대한다.
    """
    service = PlannerService(config_path=CONFIG_PATH)
    result = service.plan_question("최근 30일간 가장 많이 발생한 알람을 찾아줘")

    _assert_common_plan_shape(result.plan)
    assert result.plan.query_type == "DB_ONLY"
    _assert_step_sequence(result.plan, expected_types=["db"], expected_depends_on=[[]])


def test_planner_rag_only_live() -> None:
    """
    매뉴얼 기반 설명 질문에서 RAG_ONLY + 단일 rag step을 기대한다.
    """
    service = PlannerService(config_path=CONFIG_PATH)
    result = service.plan_question("ALM-1023 알람의 정의, 원인, 조치 방법을 매뉴얼 기준으로 찾아서 알려줘")

    _assert_common_plan_shape(result.plan)
    assert result.plan.query_type == "RAG_ONLY"
    _assert_step_sequence(result.plan, expected_types=["rag"], expected_depends_on=[[]])


def test_planner_db_then_rag_live() -> None:
    """
    DB 집계 결과를 근거로 설명 검색이 필요한 질문에서 DB_THEN_RAG를 기대한다.
    """
    service = PlannerService(config_path=CONFIG_PATH)
    result = service.plan_question("최근 30일간 가장 많이 발생한 알람을 찾고 해당 알람의 정의와 조치 방법을 알려줘")

    _assert_common_plan_shape(result.plan)
    assert result.plan.query_type == "DB_THEN_RAG"
    _assert_step_sequence(result.plan, expected_types=["db", "rag"], expected_depends_on=[[], [1]])


def test_planner_general_live() -> None:
    """
    일반 개념 설명 질문에서 GENERAL + 단일 general step을 기대한다.
    """
    service = PlannerService(config_path=CONFIG_PATH)
    result = service.plan_question("반도체 공정에서 챔버가 뭐야?")

    _assert_common_plan_shape(result.plan)
    assert result.plan.query_type == "GENERAL"
    _assert_step_sequence(result.plan, expected_types=["general"], expected_depends_on=[[]])

