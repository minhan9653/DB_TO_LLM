# 이 파일은 LLM 호출을 단일 함수로 감싸 노드가 외부 의존성 세부 구현을 모르도록 한다.
# 서비스 함수는 입력 프롬프트와 생성 옵션을 명시적으로 받아 테스트 모킹을 쉽게 만든다.
# 기존 BaseLLMClient 인터페이스를 그대로 사용해 provider 교체 비용을 줄인다.
# 예외를 숨기지 않고 그대로 전파해 상위 노드가 오류 흐름을 제어하도록 유지한다.

from __future__ import annotations

from Root_Stream.services.llm.base_llm import BaseLLMClient


def generate_text(
    *,
    llm_client: BaseLLMClient,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.0,
) -> str:
    """
    LLM 클라이언트를 호출해 텍스트를 생성한다.

    Args:
        llm_client: 생성에 사용할 LLM 클라이언트.
        system_prompt: 시스템 프롬프트.
        user_prompt: 사용자 프롬프트.
        temperature: 생성 온도.

    Returns:
        str: LLM 생성 문자열.
    """
    return llm_client.generate(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=temperature,
    ).strip()

