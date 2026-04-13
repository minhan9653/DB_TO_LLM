# 이 파일은 커맨드라인에서 그래프를 실행하는 CLI 진입점이다.
# --question으로 질문을 전달하고 --config로 설정 파일 경로를 지정할 수 있다.
# API 서버와 동일한 run_graph()를 호출해 로직 중복이 없다.
# 결과는 JSON으로 출력하며 --pretty 옵션으로 읽기 쉽게 포맷할 수 있다.

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.db_to_llm.shared.logging.logger import get_logger
from src.db_to_llm.stream.graph.runner import run_graph

logger = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    """CLI 인자를 파싱한다."""
    parser = argparse.ArgumentParser(
        description="DB_TO_LLM CLI: 자연어 질문을 DB/RAG/GENERAL 경로로 처리합니다.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python -m src.db_to_llm.stream.cli.main --question "지난달 매출 TOP 10을 알려줘"
  python -m src.db_to_llm.stream.cli.main --question "..." --config config/config.yaml --pretty
        """,
    )
    parser.add_argument(
        "--question",
        "-q",
        required=True,
        help="처리할 자연어 질문",
    )
    parser.add_argument(
        "--config",
        "-c",
        default=None,
        help="설정 파일 경로. 기본값: config/config.yaml",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="JSON 결과를 들여쓰기 포맷으로 출력",
    )
    return parser.parse_args()


def main() -> None:
    """CLI 진입점: 질문을 받아 그래프를 실행하고 결과를 출력한다."""
    args = parse_args()
    config_path = Path(args.config) if args.config else None

    logger.info("CLI 실행 시작: question=%s", args.question[:50])

    try:
        result = run_graph(
            question=args.question,
            config_path=config_path,
        )
    except Exception as error:
        logger.exception("CLI 실행 중 오류")
        print(f"오류 발생: {error}", file=sys.stderr)
        sys.exit(1)

    indent = 2 if args.pretty else None
    print(json.dumps(result, ensure_ascii=False, indent=indent))


if __name__ == "__main__":
    main()
