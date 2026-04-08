# 이 파일은 외부 API 테스트용 POST 클라이언트입니다.
# 질문 전송 시점과 요청 페이로드를 logging 으로 남깁니다.
# 응답 수신 시 상태코드와 응답 본문(JSON/텍스트)을 logging 으로 남깁니다.
# 초보자도 바로 실행할 수 있도록 인자와 기본값을 단순하게 유지했습니다.

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from typing import Any

import requests

DEFAULT_ENDPOINT = os.getenv("STREAM_ENDPOINT", "http://127.0.0.1:8000/api/query/generate")
DEFAULT_MODE = os.getenv("STREAM_MODE", "rag_prompt")
DEFAULT_TIMEOUT = int(os.getenv("STREAM_TIMEOUT", "60"))
DEFAULT_QUESTION = os.getenv(
    "STREAM_QUESTION",
    "최근 30일 동안 각 설비별 첫 오류 발생 시각과 마지막 오류 발생 시각, 그리고 총 오류 건수를 함께 보여줘.",
)


def setup_logging() -> logging.Logger:
    """테스트 클라이언트 로거를 초기화합니다."""
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    return logging.getLogger("api_test_client")


def parse_args() -> argparse.Namespace:
    """CLI 실행 인자를 파싱합니다."""
    parser = argparse.ArgumentParser(description="STREAM API 테스트 클라이언트")
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT, help="요청 대상 URL")
    parser.add_argument("--question", default=DEFAULT_QUESTION, help="질문")
    parser.add_argument("--mode", default=DEFAULT_MODE, help="mode 값")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="타임아웃(초)")
    return parser.parse_args()


def send_query(*, endpoint: str, question: str, mode: str, timeout: int, logger: logging.Logger) -> int:
    """질문을 POST 전송하고 응답 결과를 로그로 출력합니다."""
    payload: dict[str, Any] = {
        "question": question,
        "mode": mode,
    }

    logger.info("요청 전송 시작")
    logger.info("POST %s", endpoint)
    logger.info("요청 페이로드: %s", json.dumps(payload, ensure_ascii=False))

    try:
        response = requests.post(endpoint, json=payload, timeout=timeout)
    except requests.RequestException as error:
        logger.exception("요청 실패: %s", str(error))
        return 1

    logger.info("응답 수신 완료: status=%s", response.status_code)

    try:
        body = response.json()
        logger.info("응답(JSON):\n%s", json.dumps(body, ensure_ascii=False, indent=2))
    except ValueError:
        logger.info("응답(TEXT):\n%s", response.text)

    if response.ok:
        logger.info("요청 성공")
        return 0

    logger.error("요청 실패(status=%s)", response.status_code)
    return 1


def main() -> int:
    """프로그램 진입점입니다."""
    logger = setup_logging()
    args = parse_args()
    return send_query(
        endpoint=args.endpoint,
        question=args.question,
        mode=args.mode,
        timeout=args.timeout,
        logger=logger,
    )


if __name__ == "__main__":
    sys.exit(main())
