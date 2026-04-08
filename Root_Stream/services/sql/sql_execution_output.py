# 이 파일은 SQL 실행 결과 출력 형식을 공통으로 관리한다.
# main.py와 노트북 등 상위 진입점에서 동일한 결과 표현을 재사용할 수 있게 분리했다.
# 실행 결과 표 프리뷰(logger 출력)와 JSON 직렬화 보조 함수를 제공한다.
# SQL 실행 로직과 출력 로직을 분리해 main.py 책임을 최소화한다.

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
import logging
from pathlib import Path
from typing import Any

from Root_Stream.utils.logger import get_logger

module_logger = get_logger(__name__)


def _stringify_cell(value: Any) -> str:
    """표 출력용으로 셀 값을 문자열로 변환한다."""
    if value is None:
        return "NULL"
    return str(value)


def _fit_text(value: str, width: int) -> str:
    """지정된 너비를 넘는 문자열은 말줄임표로 축약한다."""
    if len(value) <= width:
        return value
    if width <= 3:
        return "." * width
    return f"{value[:width - 3]}..."


def render_execution_preview(
    result_payload: dict[str, Any],
    preview_rows: int = 20,
    logger: logging.Logger | None = None,
) -> None:
    """
    역할:
        SQL 실행 결과를 사람이 읽기 쉬운 표 형태로 logger에 출력한다.

    Args:
        result_payload: 실행 결과 payload 딕셔너리.
        preview_rows: 표로 미리보기할 최대 행 수.
        logger: 출력에 사용할 logger. 미지정 시 모듈 logger 사용.
    """
    active_logger = logger or module_logger
    execution_result = result_payload.get("execution_result")
    if not isinstance(execution_result, dict):
        active_logger.info("MSSQL 실행 프리뷰 스킵: execution_result가 없습니다.")
        return

    columns = execution_result.get("columns", [])
    rows = execution_result.get("rows", [])
    row_count = execution_result.get("row_count", 0)

    if not isinstance(columns, list) or not isinstance(rows, list):
        active_logger.warning("MSSQL 실행 프리뷰 스킵: execution_result 형식이 올바르지 않습니다.")
        return

    column_names = [str(column) for column in columns]
    preview_data = rows[:preview_rows]

    preview_lines: list[str] = []
    preview_lines.append("===== MSSQL Execution Preview =====")
    preview_lines.append(f"row_count={row_count}, preview_rows={len(preview_data)}")
    if not column_names:
        preview_lines.append("(no columns)")
        active_logger.info("\n%s", "\n".join(preview_lines))
        return
    if not preview_data:
        preview_lines.append("(empty result)")
        active_logger.info("\n%s", "\n".join(preview_lines))
        return

    max_cell_width = 40
    widths: list[int] = []
    for column_name in column_names:
        width = min(max_cell_width, len(column_name))
        for row in preview_data:
            if isinstance(row, dict):
                width = min(max_cell_width, max(width, len(_stringify_cell(row.get(column_name)))))
        widths.append(width)

    header = " | ".join(_fit_text(column_names[index], widths[index]).ljust(widths[index]) for index in range(len(column_names)))
    divider = "-+-".join("-" * widths[index] for index in range(len(column_names)))
    preview_lines.append(header)
    preview_lines.append(divider)

    for row in preview_data:
        if not isinstance(row, dict):
            continue
        line = " | ".join(
            _fit_text(_stringify_cell(row.get(column_names[index])), widths[index]).ljust(widths[index])
            for index in range(len(column_names))
        )
        preview_lines.append(line)

    if row_count > len(preview_data):
        preview_lines.append(f"... (remaining {row_count - len(preview_data)} rows omitted)")

    active_logger.info("\n%s", "\n".join(preview_lines))


def json_default_serializer(value: Any) -> Any:
    """
    역할:
        JSON 직렬화가 불가능한 값을 안전한 기본 타입으로 변환한다.

    Args:
        value: json.dumps가 처리하지 못한 원본 값.

    Returns:
        Any: 직렬화 가능한 값.
    """
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, Path):
        return str(value)

    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            pass

    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass

    return str(value)
