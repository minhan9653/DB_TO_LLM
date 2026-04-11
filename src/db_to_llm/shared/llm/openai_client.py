# 이 파일은 OpenAI Chat Completions API를 호출하는 LLM 클라이언트 구현이다.
# provider가 openai일 때 Ollama와 동일한 generate() 인터페이스로 응답을 생성한다.
# API Key는 환경변수 OPENAI_API_KEY 또는 config.openai.api_key에서 주입받는다.
# openai 패키지가 없으면 ImportError로 명확히 알려 디버깅을 돕는다.

from __future__ import annotations

from src.db_to_llm.shared.llm.base_llm import BaseLLMClient
from src.db_to_llm.shared.logging.logger import get_logger

logger = get_logger(__name__)


class OpenAIClient(BaseLLMClient):
    """OpenAI Chat Completions API를 사용하는 LLM 클라이언트."""

    provider_name = "openai"

    def __init__(self, model: str, api_key: str | None = None, request_timeout: int = 60) -> None:
        """
        OpenAI 호출에 필요한 연결 정보를 초기화한다.

        Args:
            model: 사용할 OpenAI 모델 이름. 예: "gpt-4.1-mini"
            api_key: OpenAI API Key. None이면 환경변수 OPENAI_API_KEY를 사용한다.
            request_timeout: 요청 타임아웃(초). 기본값은 60초.
        """
        self.model = model
        self.api_key = api_key
        self.request_timeout = request_timeout

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
    ) -> str:
        """
        OpenAI API를 호출해 텍스트 응답을 생성한다.

        Args:
            system_prompt: LLM 역할/지침을 정의하는 시스템 프롬프트.
            user_prompt: 실제 생성 요청 내용.
            temperature: 응답 다양성 조절값.

        Returns:
            str: LLM이 생성한 텍스트.

        Raises:
            ImportError: openai 패키지가 설치되지 않은 경우 발생한다.
            RuntimeError: API 응답에서 텍스트를 추출하지 못한 경우 발생한다.
        """
        try:
            from openai import OpenAI
        except ImportError as error:
            raise ImportError(
                "openai 패키지가 없습니다. `pip install openai`로 설치하세요."
            ) from error

        logger.info("OpenAI 호출 시작: model=%s", self.model)

        try:
            client = OpenAI(api_key=self.api_key, timeout=self.request_timeout)
            completion = client.chat.completions.create(
                model=self.model,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
        except Exception:
            logger.exception("OpenAI 호출 실패: model=%s", self.model)
            raise

        text = completion.choices[0].message.content or ""
        if not text.strip():
            raise RuntimeError("OpenAI 응답에서 텍스트를 추출하지 못했습니다.")

        logger.info("OpenAI 호출 완료: output_length=%d", len(text))
        return text
