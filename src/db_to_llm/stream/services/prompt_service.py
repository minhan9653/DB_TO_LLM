# 이 파일은 노드들이 프롬프트를 조립할 때 필요한 공통 함수들을 담는다.
# config에서 schema_context, business_rules 등을 읽어 프롬프트 변수 dict를 구성한다.
# generate_sql_node, retrieve_rag_node 등 여러 노드에서 중복 없이 재사용한다.
# PromptManager 생성도 이 파일에서 단일 진입점으로 처리한다.

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.db_to_llm.shared.logging.logger import get_logger
from src.db_to_llm.stream.prompts.prompt_manager import PromptManager

logger = get_logger(__name__)

# 이미 생성한 PromptManager를 재사용하기 위한 캐시
_prompt_manager_cache: dict[str, PromptManager] = {}


def get_prompt_manager(config: dict[str, Any]) -> PromptManager:
    """
    config에서 prompt_file 경로를 읽어 PromptManager를 반환한다.
    이미 생성된 인스턴스가 있으면 캐시에서 반환한다.

    Args:
        config: load_config()로 읽은 전체 설정 dict.

    Returns:
        PromptManager: 초기화된 프롬프트 매니저.
    """
    prompt_file_str = config.get("stream", {}).get("prompts", {}).get("prompt_file", "")

    if prompt_file_str:
        prompt_file_path = Path(prompt_file_str)
    else:
        # 기본 경로: 이 파일 기준으로 ../prompts/prompt_templates.yaml
        prompt_file_path = Path(__file__).parent.parent / "prompts" / "prompt_templates.yaml"

    cache_key = str(prompt_file_path.resolve())
    if cache_key not in _prompt_manager_cache:
        logger.info("PromptManager 생성: %s", prompt_file_path)
        _prompt_manager_cache[cache_key] = PromptManager(prompt_file_path=prompt_file_path)

    return _prompt_manager_cache[cache_key]


def build_sql_prompt_values(question: str, config: dict[str, Any]) -> dict[str, Any]:
    """
    SQL 생성 프롬프트에 필요한 변수 dict를 구성한다.

    Args:
        question: 사용자의 자연어 질문.
        config: 전체 설정 dict. stream.prompts 섹션을 참조한다.

    Returns:
        dict: question, schema_context, business_rules, additional_constraints 포함.
    """
    prompt_config = config.get("stream", {}).get("prompts", {})
    return {
        "question": question,
        "schema_context": prompt_config.get("schema_context", ""),
        "business_rules": prompt_config.get("business_rules", ""),
        "additional_constraints": prompt_config.get("additional_constraints", ""),
    }


def build_rag_prompt_values(
    question: str,
    config: dict[str, Any],
    context_block: str,
) -> dict[str, Any]:
    """
    RAG SQL 생성 프롬프트에 필요한 변수 dict를 구성한다.
    build_sql_prompt_values()에 retrieved_context를 추가한 형태다.

    Args:
        question: 사용자의 자연어 질문.
        config: 전체 설정 dict.
        context_block: rag_service.build_context_block()이 반환한 검색 결과 텍스트.

    Returns:
        dict: question, schema_context, retrieved_context 등 포함.
    """
    values = build_sql_prompt_values(question, config)
    values["retrieved_context"] = context_block
    return values
