# 이 파일은 OpenAI API를 호출하는 LLM 클라이언트 구현입니다.

# provider가 openai일 때 동일 인터페이스(generate)로 응답을 생성합니다.

# API Key는 환경 변수 또는 config에서 주입받아 코드 하드코딩을 피합니다.

# 응답 포맷 오류/호출 실패를 로깅하고 상위로 예외를 전달합니다.

from __future__ import annotations
from Root_Stream.services.llm.base_llm import BaseLLMClient
from Root_Stream.utils.logger import get_logger

logger = get_logger(__name__)


class OpenAIClient(BaseLLMClient):
    """OpenAI Chat Completions 기반 LLM 클라이언트입니다."""

    provider_name = "openai"

    def __init__(self, model: str, api_key: str | None = None, request_timeout: int = 60) -> None:
        """
        역할:
        OpenAI 호출에 필요한 초기 속성과 의존성을 설정합니다.
        
        Args:
        model (str):
        역할: `__init__` 실행에 필요한 입력값입니다.
        값: 타입 힌트 기준 `str` 값이 전달됩니다.
        전달 출처: `OpenAI 호출` 상위 호출부에서 전달됩니다.
        주의사항: 형식/범위가 함수 가정과 다르면 런타임 예외가 발생할 수 있습니다.
        api_key (str | None):
        역할: `__init__` 실행에 필요한 입력값입니다.
        값: 타입 힌트 기준 `str | None` 값이 전달됩니다.
        전달 출처: `OpenAI 호출` 상위 호출부에서 전달됩니다.
        주의사항: 형식/범위가 함수 가정과 다르면 런타임 예외가 발생할 수 있습니다.
        request_timeout (int):
        역할: `__init__` 실행에 필요한 입력값입니다.
        값: 타입 힌트 기준 `int` 값이 전달됩니다.
        전달 출처: `OpenAI 호출` 상위 호출부에서 전달됩니다.
        주의사항: 형식/범위가 함수 가정과 다르면 런타임 예외가 발생할 수 있습니다.
        
        Returns:
        None: 반환값 없이 내부 상태 업데이트, 로깅, 파일 저장 같은 부수효과를 수행합니다.
        
        Raises:
        Exception: 명시적 raise가 없어도 파일 I/O, 네트워크, 외부 라이브러리 예외가 전파될 수 있습니다.
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
        역할:
        OpenAI 호출 문맥에서 `generate` 기능을 수행합니다.
        
        Args:
        system_prompt (str):
        역할: `generate` 실행에 필요한 입력값입니다.
        값: 타입 힌트 기준 `str` 값이 전달됩니다.
        전달 출처: `OpenAI 호출` 상위 호출부에서 전달됩니다.
        주의사항: 형식/범위가 함수 가정과 다르면 런타임 예외가 발생할 수 있습니다.
        user_prompt (str):
        역할: `generate` 실행에 필요한 입력값입니다.
        값: 타입 힌트 기준 `str` 값이 전달됩니다.
        전달 출처: `OpenAI 호출` 상위 호출부에서 전달됩니다.
        주의사항: 형식/범위가 함수 가정과 다르면 런타임 예외가 발생할 수 있습니다.
        temperature (float):
        역할: `generate` 실행에 필요한 입력값입니다.
        값: 타입 힌트 기준 `float` 값이 전달됩니다.
        전달 출처: `OpenAI 호출` 상위 호출부에서 전달됩니다.
        주의사항: 형식/범위가 함수 가정과 다르면 런타임 예외가 발생할 수 있습니다.
        
        Returns:
        str: 텍스트/프롬프트/SQL 문자열 결과를 반환합니다.
        
        Raises:
        Exception: 내부 검증 실패 또는 하위 호출 오류 상황에서 발생할 수 있습니다.
        ImportError: 내부 검증 실패 또는 하위 호출 오류 상황에서 발생할 수 있습니다.
        RuntimeError: 내부 검증 실패 또는 하위 호출 오류 상황에서 발생할 수 있습니다.
        """
        try:
            from openai import OpenAI

        except Exception as error:
            raise ImportError("openai provider를 사용하려면 openai 패키지를 설치하세요.") from error

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

            text = completion.choices[0].message.content or ""

        except Exception:
            logger.exception("OpenAI 호출 실패: model=%s", self.model)

            raise

        if not text.strip():
            raise RuntimeError("OpenAI 응답에서 텍스트를 추출하지 못했습니다.")

        logger.info("OpenAI 호출 완료: output_length=%d", len(text))
        return text.strip()
