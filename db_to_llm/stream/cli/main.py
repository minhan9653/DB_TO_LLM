# 이 파일은 LangGraph 기반 Stream 워크플로의 CLI 진입점을 제공한다.
# 기존 Root_Stream.main과 동일하게 질문/설정/DB실행 옵션을 받아 결과를 출력한다.
# 실제 실행은 graph runner를 호출해 API/Notebook과 동일한 코드 경로를 공유한다.
# 출력은 JSON으로 통일해 자동화 스크립트와 실험 환경에서 재사용하기 쉽게 유지한다.

from __future__ import annotations

import argparse
import json
from pathlib import Path

from db_to_llm.stream.graph.runner import run_stream_graph


def parse_args() -> argparse.Namespace:
    """
    Stream CLI 실행 인자를 파싱한다.

    Returns:
        argparse.Namespace: CLI 인자 객체.
    """
    parser = argparse.ArgumentParser(description="Run Stream LangGraph workflow.")
    parser.add_argument("--question", type=str, required=True, help="사용자 자연어 질문")
    parser.add_argument("--config", type=str, default="", help="stream config.yaml 경로")
    parser.add_argument(
        "--mode",
        type=str,
        default="auto",
        help="auto | natural | prompt | rag_prompt",
    )
    parser.add_argument("--execute-sql", action="store_true", help="검증 후 DB 실행 여부")
    return parser.parse_args()


def main() -> None:
    """
    LangGraph Stream 워크플로를 실행하고 JSON 결과를 출력한다.
    """
    args = parse_args()
    config_path = Path(args.config).resolve() if args.config else None
    result = run_stream_graph(
        question=args.question,
        config_path=config_path,
        mode=args.mode,
        execute_sql=args.execute_sql,
    )
    print(json.dumps(result.payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

