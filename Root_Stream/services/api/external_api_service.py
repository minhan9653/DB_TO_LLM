# 이 파일은 외부 API 호출과 응답 파싱을 담당하는 서비스입니다.

# api_result mode에서 question을 API로 전달하고 응답을 표준화합니다.

# 응답 내 query 필드 우선 추출 규칙을 중앙에서 처리합니다.

# API 실패/응답 파싱 실패를 명확한 예외와 로그로 전달합니다.

from __future__ import annotations
import json
from typing import Any
import requests
from Root_Stream.utils.logger import get_logger

logger = get_logger(__name__)


class ExternalApiService:
    """외부 API 호출 및 응답 파싱 서비스입니다."""

    def __init__(self, endpoint: str, timeout: int = 10, method: str = "POST", headers: dict[str, Any] | None = None):
        """
        역할:
        외부 API 연동에 필요한 초기 속성과 의존성을 설정합니다.
        
        Args:
        endpoint (str):
        역할: 호출할 외부 API 주소입니다.
        값: 문자열 URL입니다.
        전달 출처: config의 `api.endpoint`에서 전달됩니다.
        주의사항: 빈 값이나 오타 URL이면 네트워크 호출이 실패합니다.
        timeout (int):
        역할: 요청 제한 시간(초)입니다.
        값: 정수입니다.
        전달 출처: config `timeout` 값에서 전달됩니다.
        주의사항: 너무 짧으면 정상 응답도 타임아웃으로 실패할 수 있습니다.
        method (str):
        역할: 외부 API 호출 HTTP 메서드입니다.
        값: `GET`/`POST` 같은 문자열입니다.
        전달 출처: config `api.method`에서 전달됩니다.
        주의사항: 지원하지 않는 값이면 내부 분기에서 예외가 발생합니다.
        headers (dict[str, Any] | None):
        역할: 외부 API 요청 헤더입니다.
        값: `dict[str, Any] | None`입니다.
        전달 출처: config `api.headers`에서 전달됩니다.
        주의사항: 민감 토큰이 로그에 노출되지 않게 주의해야 합니다.
        
        Returns:
        Any: 외부 API 연동 계산 결과를 `Any` 타입으로 반환합니다.
        
        Raises:
        Exception: 명시적 raise가 없어도 파일 I/O, 네트워크, 외부 라이브러리 예외가 전파될 수 있습니다.
        """

        self.endpoint = endpoint

        self.timeout = timeout

        self.method = method.strip().upper()

        self.headers = headers or {}

    def call(self, question: str) -> Any:
        """
        역할:
        외부 API 연동 문맥에서 `call` 기능을 수행합니다.
        
        Args:
        question (str):
        역할: 사용자 자연어 질문 본문입니다.
        값: 일반 문자열입니다.
        전달 출처: CLI 인자 또는 API/노트북 호출부에서 전달됩니다.
        주의사항: 빈 문자열이면 프롬프트 품질이 크게 떨어지거나 검증 예외가 발생합니다.
        
        Returns:
        Any: 외부 API 연동 계산 결과를 `Any` 타입으로 반환합니다.
        
        Raises:
        Exception: 내부 검증 실패 또는 하위 호출 오류 상황에서 발생할 수 있습니다.
        """

        logger.info("외부 API 호출 시작: endpoint=%s, method=%s", self.endpoint, self.method)

        payload = {"question": question}
        try:
            if self.method == "GET":
                response = requests.get(

                    self.endpoint,

                    params=payload,

                    headers=self.headers,

                    timeout=self.timeout,

                )

            else:
                response = requests.post(

                    self.endpoint,

                    json=payload,

                    headers=self.headers,

                    timeout=self.timeout,

                )

            response.raise_for_status()

        except Exception:
            logger.exception("외부 API 호출 실패: endpoint=%s", self.endpoint)

            raise

        content_type = response.headers.get("Content-Type", "")
        if "application/json" in content_type.lower():
            try:
                result = response.json()

            except Exception:
                logger.exception("외부 API JSON 파싱 실패")

                raise

        else:
            result = response.text

        logger.info("외부 API 호출 완료")
        return result

    @staticmethod

    def extract_query(api_result: Any) -> str | None:
        """
        역할:
        외부 API 연동에서 필요한 핵심 텍스트/필드를 추출합니다.
        
        Args:
        api_result (Any):
        역할: `extract_query` 실행에 필요한 입력값입니다.
        값: 타입 힌트 기준 `Any` 값이 전달됩니다.
        전달 출처: `외부 API 연동` 상위 호출부에서 전달됩니다.
        주의사항: 형식/범위가 함수 가정과 다르면 런타임 예외가 발생할 수 있습니다.
        
        Returns:
        str | None: 외부 API 연동 계산 결과를 `str | None` 타입으로 반환합니다.
        
        Raises:
        Exception: 명시적 raise가 없어도 파일 I/O, 네트워크, 외부 라이브러리 예외가 전파될 수 있습니다.
        """
        if isinstance(api_result, str):
            text = api_result.strip()
            return text if text else None

        if isinstance(api_result, dict):
            direct_query = api_result.get("query")
            if isinstance(direct_query, str) and direct_query.strip():
                return direct_query.strip()

            data_value = api_result.get("data")
            if isinstance(data_value, dict):
                nested_query = data_value.get("query")
                if isinstance(nested_query, str) and nested_query.strip():
                    return nested_query.strip()

            message_value = api_result.get("message")
            if isinstance(message_value, str) and message_value.strip():
                return message_value.strip()

        return None

    @staticmethod

    def stringify(api_result: Any) -> str:
        """
        역할:
        외부 API 연동 문맥에서 `stringify` 기능을 수행합니다.
        
        Args:
        api_result (Any):
        역할: `stringify` 실행에 필요한 입력값입니다.
        값: 타입 힌트 기준 `Any` 값이 전달됩니다.
        전달 출처: `외부 API 연동` 상위 호출부에서 전달됩니다.
        주의사항: 형식/범위가 함수 가정과 다르면 런타임 예외가 발생할 수 있습니다.
        
        Returns:
        str: 텍스트/프롬프트/SQL 문자열 결과를 반환합니다.
        
        Raises:
        Exception: 명시적 raise가 없어도 파일 I/O, 네트워크, 외부 라이브러리 예외가 전파될 수 있습니다.
        """
        if isinstance(api_result, str):
            return api_result

        return json.dumps(api_result, ensure_ascii=False, default=str)
