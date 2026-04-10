# 이 파일은 생성된 SQL에 대해 안전성 검증을 수행하는 노드다.
# SQL Guard를 통해 DML/DDL 차단, 단일 문장, SELECT 전용 규칙을 강제한다.
# 검증 결과는 상태에 구조화해 DB 실행 분기 조건으로 바로 사용할 수 있게 만든다.
# 검증 실패 시 그래프를 멈추지 않고 최종 응답 노드로 넘어가 원인을 안내하도록 설계한다.

from __future__ import annotations

from db_to_llm.common.logging.logger import get_logger
from db_to_llm.stream.graph.state import StreamGraphState
from db_to_llm.stream.nodes.node_helpers import append_error, append_trace, get_runtime
from db_to_llm.stream.services.sql_service import validate_sql

logger = get_logger(__name__)


def sql_validation_node(state: StreamGraphState) -> StreamGraphState:
    """
    generated_sql을 SQL Guard로 검증하고 결과를 상태에 저장한다.

    Args:
        state: 현재 그래프 상태.

    Returns:
        StreamGraphState: sql_validation_result/validated_sql 업데이트 상태 조각.
    """
    runtime = get_runtime(state)
    generated_sql = str(state.get("generated_sql") or "")
    allow_only_select = bool(runtime.config.get("sql", {}).get("allow_only_select", True))
    validation_result = validate_sql(sql=generated_sql, allow_only_select=allow_only_select)

    if not validation_result["is_valid"]:
        logger.warning("SQL 검증 실패: %s", validation_result["error"])
        return {
            "sql_validation_result": validation_result,
            "validated_sql": None,
            "errors": append_error(state, f"sql_validation_error: {validation_result['error']}"),
            "debug_trace": append_trace(state, "sql_validation_node:invalid"),
        }

    return {
        "sql_validation_result": validation_result,
        "validated_sql": validation_result["validated_sql"],
        "debug_trace": append_trace(state, "sql_validation_node"),
    }

