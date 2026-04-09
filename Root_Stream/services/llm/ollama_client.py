# 이 파일은 Ollama HTTP API를 호출하는 LLM 클라이언트 구현입니다.

# 기본 provider로 사용되며 config의 model/base_url 값을 따릅니다.

# 네트워크/응답 포맷 예외를 명확히 로그로 남기고 예외를 전달합니다.

# 최종적으로 mode가 재사용할 generate 인터페이스를 제공합니다.

from __future__ import annotations
import json
from typing import Any
import requests
from Root_Stream.services.llm.base_llm import BaseLLMClient
from Root_Stream.utils.logger import get_logger

logger = get_logger(__name__)


class OllamaClient(BaseLLMClient):
    """Ollama API 기반 LLM 클라이언트입니다."""

    provider_name = "ollama"

    def __init__(self, model: str, base_url: str, request_timeout: int = 300) -> None:
        """
        역할:
        Ollama 호출에 필요한 초기 속성과 의존성을 설정합니다.
        
        Args:
        model (str):
        역할: `__init__` 실행에 필요한 입력값입니다.
        값: 타입 힌트 기준 `str` 값이 전달됩니다.
        전달 출처: `Ollama 호출` 상위 호출부에서 전달됩니다.
        주의사항: 형식/범위가 함수 가정과 다르면 런타임 예외가 발생할 수 있습니다.
        base_url (str):
        역할: `__init__` 실행에 필요한 입력값입니다.
        값: 타입 힌트 기준 `str` 값이 전달됩니다.
        전달 출처: `Ollama 호출` 상위 호출부에서 전달됩니다.
        주의사항: 형식/범위가 함수 가정과 다르면 런타임 예외가 발생할 수 있습니다.
        request_timeout (int):
        역할: `__init__` 실행에 필요한 입력값입니다.
        값: 타입 힌트 기준 `int` 값이 전달됩니다.
        전달 출처: `Ollama 호출` 상위 호출부에서 전달됩니다.
        주의사항: 형식/범위가 함수 가정과 다르면 런타임 예외가 발생할 수 있습니다.
        
        Returns:
        None: 반환값 없이 내부 상태 업데이트, 로깅, 파일 저장 같은 부수효과를 수행합니다.
        
        Raises:
        Exception: 명시적 raise가 없어도 파일 I/O, 네트워크, 외부 라이브러리 예외가 전파될 수 있습니다.
        """

        self.model = model

        self.base_url = base_url.rstrip("/")

        self.request_timeout = request_timeout

    def generate(

        self,

        *,

        system_prompt: str,

        user_prompt: str,

        temperature: float = 0.0,

    ) -> str:
        """
        역할:
        Ollama 호출 문맥에서 `generate` 기능을 수행합니다.
        
        Args:
        system_prompt (str):
        역할: `generate` 실행에 필요한 입력값입니다.
        값: 타입 힌트 기준 `str` 값이 전달됩니다.
        전달 출처: `Ollama 호출` 상위 호출부에서 전달됩니다.
        주의사항: 형식/범위가 함수 가정과 다르면 런타임 예외가 발생할 수 있습니다.
        user_prompt (str):
        역할: `generate` 실행에 필요한 입력값입니다.
        값: 타입 힌트 기준 `str` 값이 전달됩니다.
        전달 출처: `Ollama 호출` 상위 호출부에서 전달됩니다.
        주의사항: 형식/범위가 함수 가정과 다르면 런타임 예외가 발생할 수 있습니다.
        temperature (float):
        역할: `generate` 실행에 필요한 입력값입니다.
        값: 타입 힌트 기준 `float` 값이 전달됩니다.
        전달 출처: `Ollama 호출` 상위 호출부에서 전달됩니다.
        주의사항: 형식/범위가 함수 가정과 다르면 런타임 예외가 발생할 수 있습니다.
        
        Returns:
        str: 텍스트/프롬프트/SQL 문자열 결과를 반환합니다.
        
        Raises:
        Exception: 내부 검증 실패 또는 하위 호출 오류 상황에서 발생할 수 있습니다.
        RuntimeError: 내부 검증 실패 또는 하위 호출 오류 상황에서 발생할 수 있습니다.
        ValueError: 내부 검증 실패 또는 하위 호출 오류 상황에서 발생할 수 있습니다.
        """

        endpoint = f"{self.base_url}/api/chat"

        payload: dict[str, Any] = {

            "model": self.model,

            "stream": False,

            "options": {"temperature": temperature},

            "messages": [

                {"role": "system", "content": system_prompt},

                {"role": "user", "content": user_prompt},

            ],

        }

        logger.info("Ollama 호출 시작: model=%s, endpoint=%s", self.model, endpoint)
        try:
            response = requests.post(endpoint, json=payload, timeout=self.request_timeout)

        except Exception:
            logger.exception("Ollama 호출 실패: model=%s", self.model)

            raise

        if response.status_code >= 400:
            error_message = self._extract_error_message(response)

            logger.error(

                "Ollama 호출 오류: status=%d, model=%s, message=%s",

                response.status_code,

                self.model,

                error_message,

            )
            if response.status_code == 404 and "not found" in error_message.lower() and "model" in error_message.lower():
                raise ValueError(

                    f"Ollama 모델을 찾을 수 없습니다: {self.model}. "

                    f"`ollama list`로 모델 확인 후 config의 ollama.model을 변경하거나 "

                    f"`ollama pull {self.model}`로 모델을 내려받으세요."

                )

            response.raise_for_status()

        try:
            body: dict[str, Any] = response.json()

        except Exception:
            logger.exception("Ollama 응답 JSON 파싱 실패")

            raise

        text = self._extract_text(body)
        if not text.strip():
            raise RuntimeError("Ollama 응답에서 텍스트를 추출하지 못했습니다.")

        logger.info("Ollama 호출 완료: output_length=%d", len(text))
        return text.strip()

    @staticmethod

    def _extract_text(body: dict[str, Any]) -> str:
        """
        역할:
        Ollama 호출 문맥에서 `_extract_text` 기능을 수행합니다.
        
        Args:
        body (dict[str, Any]):
        역할: `_extract_text` 실행에 필요한 입력값입니다.
        값: 타입 힌트 기준 `dict[str, Any]` 값이 전달됩니다.
        전달 출처: `Ollama 호출` 상위 호출부에서 전달됩니다.
        주의사항: 형식/범위가 함수 가정과 다르면 런타임 예외가 발생할 수 있습니다.
        
        Returns:
        str: 텍스트/프롬프트/SQL 문자열 결과를 반환합니다.
        
        Raises:
        Exception: 명시적 raise가 없어도 파일 I/O, 네트워크, 외부 라이브러리 예외가 전파될 수 있습니다.
        """

        message = body.get("message")
        if isinstance(message, dict):
            content = message.get("content")
            if isinstance(content, str):
                return content

        response_text = body.get("response")
        if isinstance(response_text, str):
            return response_text

        return ""

    @staticmethod

    def _extract_error_message(response: requests.Response) -> str:
        """
        역할:
        Ollama 호출 문맥에서 `_extract_error_message` 기능을 수행합니다.
        
        Args:
        response (requests.Response):
        역할: `_extract_error_message` 실행에 필요한 입력값입니다.
        값: 타입 힌트 기준 `requests.Response` 값이 전달됩니다.
        전달 출처: `Ollama 호출` 상위 호출부에서 전달됩니다.
        주의사항: 형식/범위가 함수 가정과 다르면 런타임 예외가 발생할 수 있습니다.
        
        Returns:
        str: 텍스트/프롬프트/SQL 문자열 결과를 반환합니다.
        
        Raises:
        Exception: 명시적 raise가 없어도 파일 I/O, 네트워크, 외부 라이브러리 예외가 전파될 수 있습니다.
        """
        try:
            payload = response.json()
            if isinstance(payload, dict):
                message = payload.get("error")
                if isinstance(message, str) and message.strip():
                    return message.strip()

                return json.dumps(payload, ensure_ascii=False, default=str)

        except Exception:
            pass

        return response.text.strip() or "unknown error"
