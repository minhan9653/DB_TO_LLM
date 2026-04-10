# 이 파일은 SQL 검증 이후 선택적으로 DB 실행을 수행하는 노드다.
# execute_sql 옵션이 켜진 경우에만 호출되며, 검증 SQL을 그대로 실행한다.
# 실행 결과는 표준 payload(columns/row_count/rows)로 상태에 저장한다.
# DB 오류는 상태 errors에 누적하고 최종 응답 단계에서 사용자에게 전달할 수 있게 한다.

from __future__ import annotations

from db_to_llm.common.logging.logger import get_logger
from db_to_llm.stream.graph.state import StreamGraphState
from db_to_llm.stream.nodes.node_helpers import append_error, append_trace, get_runtime
from db_to_llm.stream.services.sql_service import execute_sql

logger = get_logger(__name__)


def db_execute_node(state: StreamGraphState) -> StreamGraphState:
    """
    validated_sql을 실제 DB에서 실행해 결과 payload를 저장한다.

    Args:
        state: 현재 그래프 상태.

    Returns:
        StreamGraphState: execution_result/db_rows 업데이트 상태 조각.
    """
    runtime = get_runtime(state)
    validated_sql = str(state.get("validated_sql") or "").strip()
    if not validated_sql:
        return {
            "execution_result": {"columns": [], "row_count": 0, "rows": []},
            "db_rows": [],
            "debug_trace": append_trace(state, "db_execute_node:skip"),
        }

    try:
        execution_result = execute_sql(validated_sql=validated_sql, config_path=runtime.config_path)
    except Exception as error:
        logger.exception("DB 실행 실패")
        return {
            "execution_result": {"columns": [], "row_count": 0, "rows": []},
            "db_rows": [],
            "errors": append_error(state, f"db_execute_error: {error}"),
            "debug_trace": append_trace(state, "db_execute_node:error"),
        }

    return {
        "execution_result": execution_result,
        "db_rows": list(execution_result.get("rows", [])),
        "debug_trace": append_trace(state, "db_execute_node"),
    }

