# 이 파일은 Stream CLI의 호환 진입점으로 LangGraph runner를 호출한다.
# 기존 실행 옵션(question/config/execute-sql)을 유지하면서 내부 구현만 교체한다.
# 출력 포맷은 JSON으로 통일해 기존 스크립트/노트북에서 그대로 파싱할 수 있다.
# 실제 오케스트레이션은 db_to_llm.stream.graph.runner가 전담한다.

from __future__ import annotations

import argparse
import json
from pathlib import Path

from db_to_llm.stream.graph.runner import run_stream_graph


def parse_args() -> argparse.Namespace:
    """
    Stream CLI 실행 인자를 파싱한다.

    Returns:
        argparse.Namespace: 파싱된 CLI 인자.
    """
    parser = argparse.ArgumentParser(description="Run STREAM stage with LangGraph orchestration.")
    parser.add_argument(
        "--config",
        type=str,
        default=str(Path(__file__).resolve().parent / "config" / "config.yaml"),
        help="Path to stream config.yaml",
    )
    parser.add_argument("--question", type=str, required=True, help="User natural language question")
    parser.add_argument("--mode", type=str, default="auto", help="auto | natural | prompt | rag_prompt")
    parser.add_argument("--execute-sql", action="store_true", help="Execute generated SQL after validation.")
    return parser.parse_args()


def main() -> None:
    """
    Stream LangGraph 워크플로를 실행하고 최종 payload를 JSON으로 출력한다.
    """
    args = parse_args()
    config_path = Path(args.config).resolve()
    result = run_stream_graph(
        question=args.question,
        config_path=config_path,
        mode=args.mode,
        execute_sql=args.execute_sql,
    )
    print(json.dumps(result.payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

