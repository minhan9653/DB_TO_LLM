# 이 파일은 LangGraph 라우팅 함수(route_by_plan, route_after_sql_validation)을 검증한다.
# Planner 결과/옵션 조합에 따라 기대 노드로 분기하는지 빠르게 확인한다.
# 실제 노드 실행 없이 분기 규칙만 독립 테스트해 디버깅 범위를 줄인다.
# mode 강제 지정과 자동 라우팅 동작을 모두 회귀 테스트 대상으로 포함한다.

from __future__ import annotations

from db_to_llm.stream.graph.routes import route_after_sql_validation, route_by_plan


def test_route_by_plan_uses_explicit_mode() -> None:
    """
    명시 mode가 있으면 query_type보다 우선 적용되는지 확인한다.
    """
    assert route_by_plan({"mode": "natural"}) == "natural_llm_node"
    assert route_by_plan({"mode": "prompt"}) == "prompt_llm_node"
    assert route_by_plan({"mode": "rag_prompt"}) == "rag_retrieve_node"


def test_route_by_plan_uses_query_type_when_mode_auto() -> None:
    """
    mode=auto일 때 query_type 기반 라우팅이 동작하는지 확인한다.
    """
    assert route_by_plan({"mode": "auto", "query_type": "GENERAL"}) == "natural_llm_node"
    assert route_by_plan({"mode": "auto", "query_type": "DB_ONLY"}) == "prompt_llm_node"
    assert route_by_plan({"mode": "auto", "query_type": "DB_THEN_RAG"}) == "rag_retrieve_node"


def test_route_after_sql_validation() -> None:
    """
    SQL 검증 이후 DB 실행 분기 조건이 올바른지 확인한다.
    """
    assert (
        route_after_sql_validation(
            {
                "execute_sql": True,
                "sql_validation_result": {"is_valid": True},
                "validated_sql": "SELECT 1",
            }
        )
        == "db_execute_node"
    )
    assert (
        route_after_sql_validation(
            {
                "execute_sql": False,
                "sql_validation_result": {"is_valid": True},
                "validated_sql": "SELECT 1",
            }
        )
        == "final_response_node"
    )

