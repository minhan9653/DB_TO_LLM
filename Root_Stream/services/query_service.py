# 이 파일은 기존 API/CLI가 사용하던 SQL 생성 진입점을 호환 유지하기 위한 래퍼다.
# 내부 구현은 LangGraph runner를 호출해 단일 오케스트레이션 경로를 재사용한다.
# 외부 모듈은 기존 함수명(generate_stream_query)을 그대로 사용할 수 있다.
# mode 별 별칭 해석 규칙도 유지해 기존 클라이언트 변경 없이 동작하도록 한다.

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from db_to_llm.stream.graph.runner import run_sql_generation_only
from db_to_llm.common.logging.logger import get_logger

logger = get_logger(__name__)

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "config.yaml"

PUBLIC_TO_INTERNAL_MODE = {
    "natural": "natural_llm",
    "prompt": "prompt_llm",
    "rag_prompt": "rag_prompt_llm",
    "natural_llm": "natural_llm",
    "prompt_llm": "prompt_llm",
    "rag_prompt_llm": "rag_prompt_llm",
}

INTERNAL_TO_PUBLIC_MODE = {
    "natural": "natural",
    "prompt": "prompt",
    "rag_prompt": "rag_prompt",
    "natural_llm": "natural",
    "prompt_llm": "prompt",
    "rag_prompt_llm": "rag_prompt",
}


@dataclass
class QueryGenerationResult:
    """기존 API 스펙 호환용 SQL 생성 결과 모델."""

    success: bool
    mode: str
    question: str
    generated_query: str


def resolve_internal_mode(mode: str | None) -> str:
    """
    외부 mode 별칭을 내부 표준 mode로 변환한다.

    Args:
        mode: 요청 mode 문자열.

    Returns:
        str: 내부 mode(natural/prompt/rag_prompt).
    """
    requested_mode = (mode or "prompt").strip().lower()
    internal_mode = PUBLIC_TO_INTERNAL_MODE.get(requested_mode)
    if internal_mode is None:
        available_modes = ", ".join(sorted({"natural", "prompt", "rag_prompt"}))
        raise ValueError(f"지원하지 않는 mode입니다: {requested_mode}. 지원 모드: {available_modes}")
    return internal_mode


def to_public_mode(internal_mode: str) -> str:
    """
    내부 mode 문자열을 외부 API 응답용 mode로 변환한다.

    Args:
        internal_mode: 내부 mode 문자열.

    Returns:
        str: 외부 응답용 mode 문자열.
    """
    return INTERNAL_TO_PUBLIC_MODE.get(internal_mode, internal_mode)


def generate_stream_query(
    *,
    question: str,
    mode: str | None = "prompt",
    config_path: str | Path | None = None,
) -> QueryGenerationResult:
    """
    LangGraph 기반 워크플로를 실행해 SQL 생성 결과를 반환한다.

    Args:
        question: 사용자 질문.
        mode: 요청 모드.
        config_path: stream config 경로.

    Returns:
        QueryGenerationResult: SQL 생성 결과 모델.
    """
    clean_question = question.strip()
    if not clean_question:
        raise ValueError("question 값은 비어 있을 수 없습니다.")

    selected_mode = resolve_internal_mode(mode)
    selected_config_path = Path(config_path or DEFAULT_CONFIG_PATH).resolve()
    logger.info("query_service 실행: mode=%s, config=%s", selected_mode, selected_config_path)

    result = run_sql_generation_only(
        question=clean_question,
        config_path=selected_config_path,
        mode=selected_mode,
    )

    return QueryGenerationResult(
        success=bool(result.get("success", False)),
        mode=to_public_mode(str(result.get("mode", selected_mode))),
        question=clean_question,
        generated_query=str(result.get("generated_query", "")),
    )
