# 이 파일은 Ollama HTTP API를 호출하는 LLM 클라이언트 구현이다.
# 기본 provider로 사용되며 config의 ollama.model, ollama.base_url 값을 따른다.
# 네트워크 오류, HTTP 오류, 응답 파싱 오류를 세분화해 로그로 남기고 예외를 전달한다.
# BaseLLMClient.generate() 인터페이스를 구현해 provider 교체를 쉽게 만든다.

from __future__ import annotations

import json
from typing import Any

import requests

from src.db_to_llm.shared.llm.base_llm import BaseLLMClient
from src.db_to_llm.shared.logging.logger import get_logger

logger = get_logger(__name__)


class OllamaClient(BaseLLMClient):
    """Ollama REST API를 사용하는 LLM 클라이언트."""

    provider_name = "ollama"

    def __init__(self, model: str, base_url: str, request_timeout: int = 60) -> None:
        """
        Ollama 호출에 필요한 연결 정보를 초기화한다.

        Args:
            model: 사용할 Ollama 모델 이름. 예: "qwen2.5:14b"
            base_url: Ollama API 서버 주소. 예: "http://127.0.0.1:11434"
            request_timeout: 요청 타임아웃(초). 기본값은 60초.
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
        Ollama API를 호출해 텍스트 응답을 생성한다.

        Args:
            system_prompt: LLM 역할/지침을 정의하는 시스템 프롬프트.
            user_prompt: 실제 생성 요청 내용.
            temperature: 응답 다양성 조절값. 0이면 일관된 답변을 생성한다.

        Returns:
            str: LLM이 생성한 텍스트.

        Raises:
            ValueError: 모델을 찾을 수 없는 경우 발생한다.
            RuntimeError: 응답에서 텍스트를 추출하지 못한 경우 발생한다.
            requests.RequestException: 네트워크 오류 발생 시 전파된다.
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
                "Ollama HTTP 오류: status=%d, model=%s, message=%s",
                response.status_code,
                self.model,
                error_message,
            )
            # 404 + "model not found" 메시지면 사용자 친화적인 오류 메시지 제공
            if response.status_code == 404 and "model" in error_message.lower():
                raise ValueError(
                    f"Ollama 모델을 찾을 수 없습니다: {self.model}. "
                    f"`ollama list`로 모델을 확인하거나 "
                    f"`ollama pull {self.model}`로 다운로드하세요."
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
        return text

    def _extract_text(self, body: dict[str, Any]) -> str:
        """Ollama 응답 JSON에서 생성된 텍스트를 추출한다."""
        message = body.get("message", {})
        if isinstance(message, dict):
            return str(message.get("content", ""))
        return str(body.get("response", ""))

    def _extract_error_message(self, response: requests.Response) -> str:
        """응답에서 에러 메시지를 추출한다. 실패하면 상태 코드를 반환한다."""
        try:
            error_body = response.json()
            return str(error_body.get("error", response.text[:200]))
        except Exception:
            return response.text[:200]
