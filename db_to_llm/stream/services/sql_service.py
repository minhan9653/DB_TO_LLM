# 이 파일은 SQL 생성 후 검증/실행/요약까지의 비즈니스 로직을 서비스 함수로 제공한다.
# 노드는 상태 분기와 호출 순서만 담당하고 SQL 세부 처리는 이 계층에 위임한다.
# SQL Guard를 반드시 거치도록 기본 흐름을 강제해 우회 실행을 방지한다.
# DB 실행 의존성은 기존 Root_Stream SQL 서비스 구현을 재사용해 기능 호환을 유지한다.

from __future__ import annotations

from pathlib import Path
from typing import Any

from Root_Stream.services.sql.sql_guard import SqlGuard
from db_to_llm.common.logging.logger import get_logger

logger = get_logger(__name__)


def validate_sql(*, sql: str, allow_only_select: bool = True) -> dict[str, Any]:
    """
    SQL Guard로 SQL을 검증하고 결과를 표준 dict로 반환한다.

    Args:
        sql: 검증 대상 SQL.
        allow_only_select: SELECT 전용 제한 여부.

    Returns:
        dict[str, Any]: is_valid/validated_sql/error 필드 포함 결과.
    """
    if not sql.strip():
        return {"is_valid": False, "validated_sql": None, "error": "generated_sql이 비어 있습니다."}

    guard = SqlGuard(allow_only_select=allow_only_select)
    try:
        validated_sql = guard.validate_query_sql(sql)
    except Exception as error:
        logger.exception("SQL 검증 실패")
        return {"is_valid": False, "validated_sql": None, "error": str(error)}
    return {"is_valid": True, "validated_sql": validated_sql, "error": None}


def execute_sql(*, validated_sql: str, config_path: Path) -> dict[str, Any]:
    """
    검증된 SQL을 DB에서 실행하고 payload 형태로 반환한다.

    Args:
        validated_sql: SQL Guard 통과 SQL.
        config_path: stream config 경로.

    Returns:
        dict[str, Any]: columns/row_count/rows 포함 실행 결과 payload.
    """
    from Root_Stream.services.sql.sql_execution_integration import (
        build_execution_payload,
        run_generated_sql_with_executor,
    )
    from Root_Stream.services.sql.sql_executor_service import create_sql_executor_from_config_path

    executor = create_sql_executor_from_config_path(config_path=config_path)
    try:
        dataframe = run_generated_sql_with_executor(generated_sql=validated_sql, executor=executor)
        return build_execution_payload(dataframe)
    finally:
        executor.close()


def summarize_db_result(execution_payload: dict[str, Any]) -> dict[str, Any]:
    """
    DB 실행 payload를 요약해 후속 응답 생성 노드에서 사용 가능한 형태로 변환한다.

    Args:
        execution_payload: DB 실행 결과 payload.

    Returns:
        dict[str, Any]: 요약 결과 dict.
    """
    rows = execution_payload.get("rows", [])
    columns = execution_payload.get("columns", [])
    row_count = int(execution_payload.get("row_count", len(rows) if isinstance(rows, list) else 0))

    safe_rows = rows if isinstance(rows, list) else []
    safe_columns = columns if isinstance(columns, list) else []
    head_rows = safe_rows[:5]

    key_points: list[str] = []
    if row_count == 0:
        key_points.append("조회 결과가 없습니다.")
    else:
        key_points.append(f"총 {row_count}건 조회")
        if safe_columns:
            key_points.append(f"컬럼 수 {len(safe_columns)}개")

    summary_text = "\n".join(
        [
            f"row_count: {row_count}",
            f"columns: {safe_columns}",
            "key_points: " + "; ".join(key_points),
        ]
    )
    return {
        "row_count": row_count,
        "columns": safe_columns,
        "head_rows": head_rows,
        "key_points": key_points,
        "summary_text": summary_text,
    }
