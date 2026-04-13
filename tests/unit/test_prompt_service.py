# 이 파일은 프롬프트 조합 서비스 함수의 순수 로직을 단위 테스트한다.
# 질문/스키마/제약 값이 템플릿 값 dict로 올바르게 매핑되는지 검증한다.
# RAG 컨텍스트가 추가되는 rag_prompt 값 조합 규칙도 함께 확인한다.

from __future__ import annotations

from src.db_to_llm.stream.services.prompt_service import build_rag_prompt_values, build_sql_prompt_values


def test_build_sql_prompt_values() -> None:
    """기본 prompt 값 조합이 config 값을 반영하는지 확인한다."""
    config = {
        "stream": {
            "prompts": {
                "schema_context": "schema",
                "business_rules": "rules",
                "additional_constraints": "constraints",
            }
        }
    }
    values = build_sql_prompt_values(question="질문", config=config)
    assert values["question"] == "질문"
    assert values["schema_context"] == "schema"
    assert values["business_rules"] == "rules"
    assert values["additional_constraints"] == "constraints"


def test_build_rag_prompt_values() -> None:
    """RAG prompt 값 조합에 retrieved_context가 포함되는지 확인한다."""
    config = {"stream": {"prompts": {}}}
    values = build_rag_prompt_values(question="질문", config=config, context_block="ctx")
    assert values["question"] == "질문"
    assert values["retrieved_context"] == "ctx"
