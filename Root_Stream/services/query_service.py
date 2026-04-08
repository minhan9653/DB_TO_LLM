# 이 파일은 서버/CLI에서 공통으로 사용할 SQL 생성 진입점을 제공합니다.
# 기존 StreamOrchestrator를 재사용해 중복 로직을 줄이고 영향 범위를 최소화합니다.
# 요청 mode 별칭을 내부 mode 로 안전하게 변환합니다.
# 기존 main.py, mode_*.py, notebooks 흐름은 수정하지 않습니다.

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from Root_Stream.orchestrator.stream_orchestrator import build_stream_orchestrator
from Root_Stream.utils.logger import get_logger

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
    "natural_llm": "natural",
    "prompt_llm": "prompt",
    "rag_prompt_llm": "rag_prompt",
}


@dataclass
class QueryGenerationResult:
    """서버 응답으로 사용하기 위한 최소 SQL 생성 결과 모델입니다."""

    success: bool
    mode: str
    question: str
    generated_query: str


def resolve_internal_mode(mode: str | None) -> str:
    """
    요청 mode 값을 내부 orchestrator mode 값으로 변환합니다.
    """
    requested_mode = (mode or "prompt").strip().lower()
    internal_mode = PUBLIC_TO_INTERNAL_MODE.get(requested_mode)
    if internal_mode is None:
        available_modes = ", ".join(sorted({"natural", "prompt", "rag_prompt"}))
        raise ValueError(f"지원하지 않는 mode 입니다: {requested_mode}. 사용 가능 값: {available_modes}")
    return internal_mode


def to_public_mode(internal_mode: str) -> str:
    """
    내부 mode 값을 API 응답용 공개 mode 값으로 변환합니다.
    """
    return INTERNAL_TO_PUBLIC_MODE.get(internal_mode, internal_mode)


def generate_stream_query(
    *,
    question: str,
    mode: str | None = "prompt",
    config_path: str | Path | None = None,
) -> QueryGenerationResult:
    """
    기존 STREAM 오케스트레이터를 재사용해 질문을 SQL로 생성합니다.
    """
    clean_question = question.strip()
    if not clean_question:
        raise ValueError("question 값은 비어 있을 수 없습니다.")

    selected_internal_mode = resolve_internal_mode(mode)
    selected_config_path = Path(config_path or DEFAULT_CONFIG_PATH).resolve()

    logger.info(
        "STREAM 공통 생성 실행: mode=%s, config=%s",
        selected_internal_mode,
        selected_config_path,
    )

    orchestrator = build_stream_orchestrator(selected_config_path)
    orchestrator.config["mode"] = selected_internal_mode
    stream_result = orchestrator.run(clean_question)

    return QueryGenerationResult(
        success=True,
        mode=to_public_mode(stream_result.mode),
        question=stream_result.question,
        generated_query=stream_result.query,
    )
