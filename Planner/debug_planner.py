# 이 파일은 Planner 단계만 수동으로 점검하기 위한 디버그 실행 스크립트다.
# 단일 한국어 질문 1개를 입력받아 raw 응답과 파싱 결과를 출력한다.
# LLM 호출은 PlannerService를 통해 Root_Stream 기존 호출 구조를 재사용한다.
# DB 실행, RAG 검색, SQL 생성 없이 Planner JSON 품질만 확인하는 데 목적이 있다.

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Planner.planner_service import DEFAULT_CONFIG_PATH, PlannerService
from Root_Stream.utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_QUESTION = "최근 30일간 가장 많이 발생한 알람을 찾고 해당 알람의 정의와 조치 방법을 알려줘"


def parse_args() -> argparse.Namespace:
    """
    디버그 실행 인자를 파싱한다.
    """
    parser = argparse.ArgumentParser(description="Planner 단계 단독 디버그 실행 스크립트")
    parser.add_argument(
        "--config",
        type=str,
        default=str(DEFAULT_CONFIG_PATH),
        help="Root_Stream config.yaml 경로",
    )
    parser.add_argument(
        "--question",
        type=str,
        default=DEFAULT_QUESTION,
        help="Planner에 전달할 단일 질문",
    )
    return parser.parse_args()


def main() -> None:
    """
    Planner를 단일 질문으로 실행해 질문, raw 응답, 파싱 계획을 출력한다.
    """
    args = parse_args()
    config_path = Path(args.config).resolve()
    question = args.question.strip()
    if not question:
        raise ValueError("question 값은 비어 있을 수 없습니다.")

    logger.info("Planner 디버그 실행 시작: config=%s", config_path)
    service = PlannerService(config_path=config_path)

    print("=" * 100)
    print("[질문]")
    print(question)
    try:
        result = service.plan_question(question)
        print("-" * 100)
        print("[Raw Response]")
        print(result.raw_response)
        print("-" * 100)
        print("[Parsed Plan]")
        print(json.dumps(result.plan.to_dict(), ensure_ascii=False, indent=2))
    except Exception as error:
        logger.exception("Planner 디버그 실행 실패")
        print("-" * 100)
        print("[Error]")
        print(str(error))
    print("=" * 100)
    logger.info("Planner 디버그 실행 완료")


if __name__ == "__main__":
    main()
