# 이 파일은 LLM 클라이언트의 공통 인터페이스를 정의합니다.

# mode 서비스는 구체 구현 대신 이 인터페이스에만 의존합니다.

# provider 교체(ollama/openai) 시 mode 비즈니스 로직 변경을 줄입니다.

# 응답 생성 메서드 시그니처를 통일해 오케스트레이션을 단순화합니다.

from __future__ import annotations
from abc import ABC, abstractmethod


class BaseLLMClient(ABC):
    """LLM 클라이언트 공통 인터페이스입니다."""

    provider_name: str = "unknown"

    @abstractmethod

    def generate(

        self,

        *,

        system_prompt: str,

        user_prompt: str,

        temperature: float = 0.0,

    ) -> str:
        """
        역할:
        LLM 추상 인터페이스 문맥에서 `generate` 기능을 수행합니다.
        
        Args:
        system_prompt (str):
        역할: `generate` 실행에 필요한 입력값입니다.
        값: 타입 힌트 기준 `str` 값이 전달됩니다.
        전달 출처: `LLM 추상 인터페이스` 상위 호출부에서 전달됩니다.
        주의사항: 형식/범위가 함수 가정과 다르면 런타임 예외가 발생할 수 있습니다.
        user_prompt (str):
        역할: `generate` 실행에 필요한 입력값입니다.
        값: 타입 힌트 기준 `str` 값이 전달됩니다.
        전달 출처: `LLM 추상 인터페이스` 상위 호출부에서 전달됩니다.
        주의사항: 형식/범위가 함수 가정과 다르면 런타임 예외가 발생할 수 있습니다.
        temperature (float):
        역할: `generate` 실행에 필요한 입력값입니다.
        값: 타입 힌트 기준 `float` 값이 전달됩니다.
        전달 출처: `LLM 추상 인터페이스` 상위 호출부에서 전달됩니다.
        주의사항: 형식/범위가 함수 가정과 다르면 런타임 예외가 발생할 수 있습니다.
        
        Returns:
        str: 텍스트/프롬프트/SQL 문자열 결과를 반환합니다.
        
        Raises:
        NotImplementedError: 내부 검증 실패 또는 하위 호출 오류 상황에서 발생할 수 있습니다.
        """

        raise NotImplementedError
