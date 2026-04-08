# 이 파일은 STREAM 단계를 CLI에서 실행하는 공통 진입점이다.
# config.yaml을 읽어 SQL 생성 오케스트레이터를 실행한다.
# 필요 시 --execute-sql 옵션으로 생성된 SQL을 MSSQL에서 조회 실행한다.
# 실행 결과는 JSON으로 출력해 노트북/스크립트에서 재사용할 수 있게 한다.

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from Root_Stream.orchestrator.stream_orchestrator import build_stream_orchestrator
from Root_Stream.services.sql.sql_execution_hook import append_sql_execution_result
from Root_Stream.services.sql.sql_execution_output import (
    json_default_serializer,
    render_execution_preview,
)
from Root_Stream.utils.logger import get_logger

logger = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    """
    역할:
        STREAM CLI 실행 인자를 파싱한다.

    Returns:
        argparse.Namespace: config 경로, 질문, SQL 실행 여부를 포함한 실행 인자.
    """
    parser = argparse.ArgumentParser(description="Run STREAM stage for SQL generation.")
    parser.add_argument(
        "--config",
        type=str,
        default=str(Path(__file__).resolve().parent / "config" / "config.yaml"),
        help="Path to stream config.yaml",
    )
    parser.add_argument("--question", type=str, required=True, help="User natural language question")
    parser.add_argument(
        "--execute-sql",
        action="store_true",
        help="Execute generated SQL on MSSQL using database/sql settings in config.",
    )
    return parser.parse_args()


def main() -> None:
    """
    역할:
        STREAM SQL 생성 파이프라인을 실행하고 옵션에 따라 MSSQL 조회까지 수행한다.
    """
    args = parse_args()
    config_path = Path(args.config).resolve()

    logger.info("STREAM CLI 시작: config=%s", config_path)
    orchestrator = build_stream_orchestrator(config_path)
    result = orchestrator.run(args.question)
    logger.info("SQL 생성 완료")
    logger.info(result.query)
    result_payload = result.to_dict()
    result_payload = append_sql_execution_result(
        result_payload=result_payload,
        config_path=config_path,
        execute_sql=args.execute_sql,
    )
    render_execution_preview(result_payload=result_payload, preview_rows=20, logger=logger)
    print(json.dumps(result_payload, ensure_ascii=False, indent=2, default=json_default_serializer))


if __name__ == "__main__":
    main()
