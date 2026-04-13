# 이 파일은 LLM 클라이언트의 공통 인터페이스(추상 클래스)를 정의한다.
# Ollama, OpenAI 등 모든 provider 구현체는 이 클래스를 상속해야 한다.
# generate() 메서드 하나만 강제해 provider 교체를 단순하게 유지한다.
# llm_factory.py가 이 인터페이스를 반환 타입으로 사용한다.

from __future__ import annotations

from abc import ABC, abstractmethod


class BaseLLMClient(ABC):
    """모든 LLM provider 구현체가 상속하는 기본 클래스."""

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
        LLM을 호출해 텍스트 응답을 생성한다.

        Args:
            system_prompt: LLM에 역할/지침을 전달하는 시스템 프롬프트.
            user_prompt: 실제 사용자 질문 또는 생성 요청.
            temperature: 응답 다양성 조절값. 0에 가까울수록 일관된 답변을 생성한다.

        Returns:
            str: LLM이 생성한 텍스트 응답.
        """
        ...
