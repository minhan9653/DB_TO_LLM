# 이 파일은 generate_sql_node가 만든 SQL을 SELECT-only 규칙으로 검증하는 노드이다.
# sql_service.validate_sql()을 호출해 금지 키워드, 다중 구문, SELECT 외 시작을 차단한다.
# 검증 성공 시 validated_sql에 저장하고, 실패 시 오류를 기록하고 흐름을 계속 진행한다.
# execute_sql_node는 validated_sql이 있을 때만 DB 실행을 수행한다.

from __future__ import annotations

from src.db_to_llm.shared.logging.logger import get_logger
from src.db_to_llm.stream.graph.state import GraphState
from src.db_to_llm.stream.nodes.node_helpers import append_error, append_trace
from src.db_to_llm.stream.services.sql_service import validate_sql

logger = get_logger(__name__)


def validate_sql_node(state: GraphState) -> GraphState:
    """
    generated_sql을 검증해 validated_sql을 state에 저장한다.

    입력 state 키: generated_sql
    출력 state 키: validated_sql, sql_validation_passed, sql_validation_error

    Args:
        state: 현재 그래프 실행 상태.

    Returns:
        GraphState: 검증 결과가 추가된 상태.
    """
    generated_sql = state.get("generated_sql", "")
    logger.info("validate_sql_node 시작: sql_length=%d", len(generated_sql or ""))

    if not generated_sql:
        message = "검증할 SQL이 없습니다."
        logger.warning("validate_sql_node: %s", message)
        return {
            **state,
            "validated_sql": None,
            "sql_validation_passed": False,
            "sql_validation_error": message,
            "errors": append_error(state, f"validate_sql_node: {message}"),
            "trace_logs": append_trace(state, "validate_sql_node: SQL 없음"),
        }

    try:
        validated = validate_sql(generated_sql)
        logger.info("validate_sql_node 완료: 검증 통과")

        return {
            **state,
            "validated_sql": validated,
            "sql_validation_passed": True,
            "sql_validation_error": None,
            "trace_logs": append_trace(state, "validate_sql_node: 검증 통과"),
        }

    except ValueError as error:
        logger.error("validate_sql_node 검증 실패: %s", error)
        return {
            **state,
            "validated_sql": None,
            "sql_validation_passed": False,
            "sql_validation_error": str(error),
            "errors": append_error(state, f"validate_sql_node 검증 실패: {error}"),
            "trace_logs": append_trace(state, f"validate_sql_node: 검증 실패 - {error}"),
        }
