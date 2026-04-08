# 이 파일은 디버그용 고정 요청을 서버로 보내는 간단한 클라이언트입니다.
# VS Code 디버그에서 서버 브레이크포인트 확인을 빠르게 하기 위해 작성했습니다.
# 값은 상수/인자로 관리해 초보자도 수정 지점을 바로 찾을 수 있습니다.
# 민감정보는 출력하지 않고 요청/응답 상태만 로깅합니다.

from __future__ import annotations

import argparse
import json
import os

import requests

from Root_Stream.utils.logger import get_logger, setup_logger

logger = get_logger(__name__)

DEFAULT_ENDPOINT = os.getenv("STREAM_SERVER_ENDPOINT", "http://127.0.0.1:8000/api/query/generate")
DEFAULT_MODE = os.getenv("STREAM_SERVER_MODE", "prompt")
DEFAULT_TIMEOUT = int(os.getenv("STREAM_SERVER_TIMEOUT", "60"))
DEFAULT_QUESTION = os.getenv(
    "STREAM_SERVER_QUESTION",
    "최근 30일 동안 각 설비별 첫 오류 발생 시각과 마지막 오류 발생 시각, 그리고 총 오류 건수를 함께 보여줘.",
)


def parse_args() -> argparse.Namespace:
    """
    디버그 클라이언트 실행 인자를 파싱합니다.
    """
    parser = argparse.ArgumentParser(description="STREAM 서버 디버그 클라이언트")
    parser.add_argument("--endpoint", type=str, default=DEFAULT_ENDPOINT, help="요청 대상 API URL")
    parser.add_argument("--mode", type=str, default=DEFAULT_MODE, help="요청 mode")
    parser.add_argument("--question", type=str, default=DEFAULT_QUESTION, help="질문 텍스트")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="요청 타임아웃(초)")
    return parser.parse_args()


def main() -> None:
    """
    고정 질문을 서버에 POST 요청하고 응답을 로그로 출력합니다.
    """
    setup_logger()
    args = parse_args()

    payload = {
        "question": args.question,
        "mode": args.mode,
    }

    logger.info("디버그 요청 전송: endpoint=%s, mode=%s", args.endpoint, args.mode)
    response = requests.post(
        args.endpoint,
        json=payload,
        timeout=args.timeout,
    )

    logger.info("응답 수신: status=%s", response.status_code)
    response.raise_for_status()

    try:
        response_data = response.json()
        logger.info("응답 JSON:\n%s", json.dumps(response_data, ensure_ascii=False, indent=2))
    except ValueError:
        logger.warning("JSON 응답이 아니므로 원문 텍스트를 출력합니다.")
        logger.info("응답 본문:\n%s", response.text)


if __name__ == "__main__":
    main()

