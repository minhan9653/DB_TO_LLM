# 이 파일은 최종 응답 생성을 서비스 계층에서 처리하기 위한 모듈이다.
# Planner/SQL/DB/RAG 결과를 합쳐 사용자에게 전달할 최종 설명 텍스트를 생성한다.
# LLM 호출 실패 시에도 상태 요약 기반 fallback 응답을 반환해 실행을 끊지 않는다.
# query_service 순환 import를 피하기 위해 독립 구현으로 유지한다.

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from db_to_llm.common.config.runtime_config import build_runtime_services
from db_to_llm.common.logging.logger import get_logger
from db_to_llm.stream.services.llm_service import generate_text

logger = get_logger(__name__)


def generate_final_response(
    *,
    question: str,
    planner_result: dict[str, Any] | None,
    generated_sql: str | None,
    db_result_summary: dict[str, Any] | None,
    rag_docs: list[dict[str, Any]] | None,
    config_path: Path,
    errors: list[str] | None = None,
) -> dict[str, Any]:
    """
    최종 사용자 응답을 생성한다.

    Args:
        question: 사용자 질문.
        planner_result: Planner 결과.
        generated_sql: 생성된 SQL.
        db_result_summary: DB 요약 정보.
        rag_docs: RAG 문서 목록.
        config_path: stream config 경로.
        errors: 누적 오류 목록.

    Returns:
        dict[str, Any]: final_answer/errors 결과.
    """
    runtime = build_runtime_services(config_path=config_path)
    safe_errors = list(errors or [])
    safe_docs = list(rag_docs or [])

    system_prompt = (
        "너는 DB_TO_LLM 최종 응답 정리 도우미다.\n"
        "입력된 Planner/SQL/DB/RAG 정보를 기반으로 간결하고 정확한 답변을 작성해라.\n"
        "확실하지 않은 내용은 추측하지 말고 부족한 정보를 명시해라."
    )
    user_prompt = _build_user_prompt(
        question=question,
        planner_result=planner_result,
        generated_sql=generated_sql,
        db_result_summary=db_result_summary,
        rag_docs=safe_docs,
        errors=safe_errors,
    )

    try:
        final_answer = generate_text(
            llm_client=runtime.llm_client,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.2,
        )
        return {"final_answer": final_answer, "errors": []}
    except Exception as error:
        logger.exception("최종 응답 생성 실패")
        fallback_errors = [*safe_errors, str(error)]
        return {
            "final_answer": _build_fallback_answer(
                question=question,
                db_result_summary=db_result_summary,
                rag_docs=safe_docs,
                errors=fallback_errors,
            ),
            "errors": [f"final_response_error: {error}"],
        }


def _build_user_prompt(
    *,
    question: str,
    planner_result: dict[str, Any] | None,
    generated_sql: str | None,
    db_result_summary: dict[str, Any] | None,
    rag_docs: list[dict[str, Any]],
    errors: list[str],
) -> str:
    """
    최종 응답 생성용 user prompt를 구성한다.

    Args:
        question: 사용자 질문.
        planner_result: Planner 결과.
        generated_sql: 생성된 SQL.
        db_result_summary: DB 결과 요약.
        rag_docs: RAG 문서 목록.
        errors: 누적 오류.

    Returns:
        str: 최종 생성용 user prompt.
    """
    rag_preview = _build_rag_preview(rag_docs)
    planner_text = json.dumps(planner_result or {}, ensure_ascii=False, indent=2)
    return (
        f"[질문]\n{question}\n\n"
        f"[Planner]\n{planner_text}\n\n"
        f"[SQL]\n{generated_sql or '없음'}\n\n"
        f"[DB 요약]\n{(db_result_summary or {}).get('summary_text', '없음')}\n\n"
        f"[RAG]\n{rag_preview}\n\n"
        f"[오류]\n{chr(10).join(errors) if errors else '없음'}\n"
    )


def _build_rag_preview(rag_docs: list[dict[str, Any]], max_docs: int = 4) -> str:
    """
    RAG 문서 목록을 짧은 요약 텍스트로 변환한다.

    Args:
        rag_docs: RAG 문서 목록.
        max_docs: 최대 포함 문서 수.

    Returns:
        str: 요약 문자열.
    """
    if not rag_docs:
        return "없음"
    lines: list[str] = []
    for index, doc in enumerate(rag_docs[:max_docs], start=1):
        metadata = doc.get("metadata", {}) if isinstance(doc, dict) else {}
        source_name = metadata.get("source") if isinstance(metadata, dict) else None
        text = str(doc.get("text", "")).replace("\n", " ")[:200]
        lines.append(f"[{index}] source={source_name}, text={text}")
    return "\n".join(lines)


def _build_fallback_answer(
    *,
    question: str,
    db_result_summary: dict[str, Any] | None,
    rag_docs: list[dict[str, Any]],
    errors: list[str],
) -> str:
    """
    LLM 실패 시 사용할 fallback 최종 응답을 생성한다.

    Args:
        question: 사용자 질문.
        db_result_summary: DB 요약.
        rag_docs: RAG 문서 목록.
        errors: 오류 목록.

    Returns:
        str: fallback 응답.
    """
    lines = [f"질문: {question}", "", "[fallback 응답]"]
    if db_result_summary:
        lines.append(f"- DB 요약: {db_result_summary.get('summary_text', '없음')}")
    else:
        lines.append("- DB 요약: 없음")
    lines.append(f"- RAG 문서 수: {len(rag_docs)}")
    if errors:
        lines.append("- 오류:")
        for item in errors[-3:]:
            lines.append(f"  - {item}")
    return "\n".join(lines)

