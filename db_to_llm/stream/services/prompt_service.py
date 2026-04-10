# 이 파일은 SQL 생성용 프롬프트 조합 로직을 서비스 함수로 분리한다.
# 노드는 어떤 키로 어떤 값을 넣는지만 결정하고 문자열 조합은 이 계층에 위임한다.
# 기존 PromptManager를 그대로 활용해 템플릿 파일 구조를 변경하지 않는다.
# prompt_llm/rag_prompt_llm 노드가 동일 규칙을 공유하도록 중복을 제거한다.

from __future__ import annotations

from typing import Any

from Root_Stream.prompts.prompt_manager import PromptManager


def build_prompt_values(config: dict[str, Any], question: str) -> dict[str, str]:
    """
    prompt_llm 모드에 필요한 템플릿 값을 구성한다.

    Args:
        config: stream 설정 dict.
        question: 사용자 질문.

    Returns:
        dict[str, str]: prompt 템플릿 치환 값.
    """
    prompts_config = config.get("prompts", {})
    return {
        "question": question,
        "schema_context": str(prompts_config.get("schema_context", "")),
        "business_rules": str(prompts_config.get("business_rules", "")),
        "additional_constraints": str(prompts_config.get("additional_constraints", "")),
    }


def build_rag_prompt_values(config: dict[str, Any], question: str, context_block: str) -> dict[str, str]:
    """
    rag_prompt_llm 모드에 필요한 템플릿 값을 구성한다.

    Args:
        config: stream 설정 dict.
        question: 사용자 질문.
        context_block: 검색 컨텍스트 문자열.

    Returns:
        dict[str, str]: rag prompt 템플릿 치환 값.
    """
    values = build_prompt_values(config=config, question=question)
    values["retrieved_context"] = context_block
    return values


def render_prompt(
    *,
    prompt_manager: PromptManager,
    prompt_key: str,
    values: dict[str, Any],
) -> str:
    """
    PromptManager를 사용해 지정된 템플릿을 렌더링한다.

    Args:
        prompt_manager: 템플릿 관리자.
        prompt_key: 프롬프트 키.
        values: 템플릿 치환 값.

    Returns:
        str: 최종 프롬프트 문자열.
    """
    return prompt_manager.render_prompt(prompt_key, values)

