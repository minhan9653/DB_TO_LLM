# 이 파일은 Planner -> DB -> RAG -> 최종답변 전체 흐름을 한 번에 점검하기 위한 얇은 오케스트레이션 레이어다.
# 핵심 비즈니스 로직은 기존 Planner/SQL/RAG/LLM 서비스 모듈을 그대로 재사용한다.
# 노트북에서는 이 파일의 함수만 호출해서 단계별 실행 결과를 확인할 수 있다.
# DB 미연결 환경을 위한 mock 실행 경로와 문서 RAG on/off 플래그를 함께 제공한다.

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from Planner.planner_service import PlannerService
from Root_Stream.prompts.prompt_manager import PromptManager
from Root_Stream.services.llm.base_llm import BaseLLMClient
from Root_Stream.services.llm.llm_factory import create_llm_client
from Root_Stream.services.query_service import generate_stream_query
from Root_Stream.services.retrieval.chroma_retriever import ChromaRetriever
from Root_Stream.services.retrieval.embedding_service import SentenceTransformerEmbeddingService
from Root_Stream.services.sql.sql_guard import SqlGuard
from Root_Stream.utils.config_loader import load_config
from Root_Stream.utils.logger import get_logger, setup_logger
from Root_Stream.utils.path_utils import resolve_path

logger = get_logger(__name__)

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "config.yaml"

DB_QUERY_TYPES = {"DB_ONLY", "DB_THEN_RAG", "DB_THEN_GENERAL"}
DOC_RAG_QUERY_TYPES = {"RAG_ONLY", "DB_THEN_RAG", "RAG_THEN_GENERAL"}


@dataclass
class E2ERuntime:
    """E2E 실행에 필요한 공통 의존성을 담는 런타임 컨테이너."""

    config_path: Path
    config: dict[str, Any]
    project_root: Path
    prompt_manager: PromptManager
    llm_client: BaseLLMClient


def build_e2e_runtime(config_path: str | Path | None = None) -> E2ERuntime:
    """config 로드, 경로 해석, 로거 설정, PromptManager/LLM 클라이언트를 준비한다."""
    resolved_config_path = Path(config_path or DEFAULT_CONFIG_PATH).resolve()
    config = load_config(resolved_config_path)
    stream_root = resolved_config_path.parent.parent
    project_root = resolve_path(config.get("paths", {}).get("project_root", "."), stream_root)

    log_level = str(config.get("logging", {}).get("level", "INFO"))
    log_file_value = config.get("paths", {}).get("log_file")
    log_file_path = resolve_path(log_file_value, project_root) if log_file_value else None
    setup_logger(log_level=log_level, log_file_path=log_file_path)

    prompt_file_path = resolve_path(config["paths"]["prompt_file"], project_root)
    prompt_manager = PromptManager(prompt_file_path=prompt_file_path)
    llm_client = create_llm_client(config)
    return E2ERuntime(
        config_path=resolved_config_path,
        config=config,
        project_root=project_root,
        prompt_manager=prompt_manager,
        llm_client=llm_client,
    )


def run_planner_step(*, question: str, config_path: str | Path | None = None) -> dict[str, Any]:
    """Planner 단계를 실행하고 raw/parsed 결과와 query_type 정보를 반환한다."""
    clean_question = question.strip()
    if not clean_question:
        raise ValueError("질문이 비어 있습니다.")

    runtime = build_e2e_runtime(config_path=config_path)
    planner_service = PlannerService(config_path=runtime.config_path)
    planner_run = planner_service.plan_question(clean_question)
    planner_result = planner_run.plan.to_dict()
    reasoning_summary = _extract_reasoning_summary(planner_run.raw_response)

    return {
        "question": clean_question,
        "planner_raw": planner_run.raw_response,
        "planner_result": planner_result,
        "query_type": planner_run.plan.query_type,
        "reasoning_summary": reasoning_summary,
    }


def run_db_step(
    *,
    question: str,
    query_type: str,
    planner_steps: list[dict[str, Any]] | None = None,
    config_path: str | Path | None = None,
    use_mock_db_result: bool = False,
    mock_db_rows: list[dict[str, Any]] | None = None,
    sql_generation_mode: str | None = None,
) -> dict[str, Any]:
    """DB 관련 query_type일 때 SQL 생성/검증/실행/요약을 수행한다."""
    result: dict[str, Any] = {
        "generated_sql": None,
        "selected_sql_mode": None,
        "sql_validation_result": None,
        "db_rows": [],
        "db_result_summary": None,
        "errors": [],
        "executed_steps": [],
    }
    if query_type not in DB_QUERY_TYPES:
        return result

    runtime = build_e2e_runtime(config_path=config_path)
    steps = planner_steps or []
    selected_mode = _select_sql_generation_mode(
        query_type=query_type,
        planner_steps=steps,
        explicit_mode=sql_generation_mode,
    )
    result["selected_sql_mode"] = selected_mode

    try:
        query_result = generate_stream_query(
            question=question,
            mode=selected_mode,
            config_path=runtime.config_path,
        )
        generated_sql = query_result.generated_query.strip()
        result["generated_sql"] = generated_sql
        result["executed_steps"].append("sql_generation")
    except Exception as error:
        message = f"SQL 생성 실패: {error}"
        logger.exception(message)
        result["errors"].append(message)
        return result

    sql_guard = SqlGuard(
        allow_only_select=bool(runtime.config.get("sql", {}).get("allow_only_select", True)),
    )
    validated_sql = ""
    try:
        validated_sql = sql_guard.validate_query_sql(result["generated_sql"])
        result["sql_validation_result"] = {
            "is_valid": True,
            "validated_sql": validated_sql,
            "error": None,
        }
        result["executed_steps"].append("sql_validation")
    except Exception as error:
        message = f"SQL 검증 실패: {error}"
        logger.exception(message)
        result["sql_validation_result"] = {
            "is_valid": False,
            "validated_sql": None,
            "error": str(error),
        }
        result["errors"].append(message)
        return result

    execution_payload: dict[str, Any] | None = None
    if use_mock_db_result:
        rows = mock_db_rows if mock_db_rows is not None else _default_mock_db_rows()
        execution_payload = {
            "columns": list(rows[0].keys()) if rows else [],
            "row_count": len(rows),
            "rows": rows,
        }
        result["executed_steps"].append("db_execution_mock")
    else:
        try:
            from Root_Stream.services.sql.sql_execution_integration import (
                build_execution_payload,
                run_generated_sql_with_executor,
            )
            from Root_Stream.services.sql.sql_executor_service import create_sql_executor_from_config_path
        except ModuleNotFoundError as error:
            message = (
                "DB 실행 의존성 모듈이 없어 DB step을 수행할 수 없습니다. "
                f"(detail={error})"
            )
            logger.exception(message)
            result["errors"].append(message)
            return result

        executor = create_sql_executor_from_config_path(config_path=runtime.config_path)
        try:
            dataframe = run_generated_sql_with_executor(generated_sql=validated_sql, executor=executor)
            execution_payload = build_execution_payload(dataframe)
            result["executed_steps"].append("db_execution")
        except Exception as error:
            message = f"DB 실행 실패: {error}"
            logger.exception(message)
            result["errors"].append(message)
            return result
        finally:
            executor.close()

    result["db_rows"] = execution_payload["rows"] if execution_payload else []
    result["db_result_summary"] = summarize_db_execution_payload(execution_payload or {})
    result["executed_steps"].append("db_summary")
    return result


def summarize_db_execution_payload(
    execution_payload: dict[str, Any],
    *,
    preview_rows: int = 5,
) -> dict[str, Any]:
    """DB 실행 payload를 노트북 출력용 요약 포맷으로 변환한다."""
    rows = execution_payload.get("rows", [])
    columns = execution_payload.get("columns", [])
    row_count = int(execution_payload.get("row_count", len(rows) if isinstance(rows, list) else 0))

    safe_rows = rows if isinstance(rows, list) else []
    safe_columns = columns if isinstance(columns, list) else []
    head_rows = safe_rows[:preview_rows]

    key_points: list[str] = []
    if row_count == 0:
        key_points.append("조회 결과가 없습니다.")
    else:
        key_points.append(f"총 {row_count}건 조회")
        if safe_columns:
            key_points.append(f"컬럼 수 {len(safe_columns)}개")
        if head_rows and isinstance(head_rows[0], dict):
            first_row = head_rows[0]
            first_cols = list(first_row.keys())[:3]
            preview_pairs = [f"{name}={first_row.get(name)}" for name in first_cols]
            if preview_pairs:
                key_points.append("첫 행 예시: " + ", ".join(preview_pairs))

    summary_text_lines = [
        f"row_count: {row_count}",
        f"columns: {safe_columns}",
        "key_points: " + "; ".join(key_points),
    ]
    return {
        "row_count": row_count,
        "columns": safe_columns,
        "head_rows": head_rows,
        "key_points": key_points,
        "summary_text": "\n".join(summary_text_lines),
    }


def run_doc_rag_step(
    *,
    question: str,
    query_type: str,
    db_result_summary: dict[str, Any] | None = None,
    config_path: str | Path | None = None,
    use_doc_rag: bool = True,
    doc_rag_top_k: int | None = None,
) -> dict[str, Any]:
    """일반 문서 RAG 단계를 실행하고 검색 문서 목록을 반환한다."""
    result: dict[str, Any] = {
        "rag_query": None,
        "rag_docs": [],
        "rag_config": None,
        "errors": [],
        "executed_steps": [],
    }
    if query_type not in DOC_RAG_QUERY_TYPES:
        return result
    if not use_doc_rag:
        result["errors"].append("문서 RAG 플래그가 비활성화되어 RAG 단계를 건너뜁니다.")
        return result

    runtime = build_e2e_runtime(config_path=config_path)
    rag_config = _resolve_doc_retrieval_config(
        config=runtime.config,
        project_root=runtime.project_root,
        doc_rag_top_k=doc_rag_top_k,
    )
    result["rag_config"] = rag_config
    rag_query = _build_doc_rag_query(
        question=question,
        query_type=query_type,
        db_result_summary=db_result_summary,
    )
    result["rag_query"] = rag_query

    try:
        embedding_service = SentenceTransformerEmbeddingService(
            model_name=str(rag_config["embedding_model"]),
        )
        retriever = ChromaRetriever(
            persist_directory=Path(str(rag_config["chroma_path"])),
            collection_name=str(rag_config["collection_name"]),
            top_k=int(rag_config["top_k"]),
        )
        query_embedding = embedding_service.embed_query(rag_query)
        contexts = retriever.retrieve(query_embedding)
        result["rag_docs"] = [item.to_dict() for item in contexts]
        result["executed_steps"].append("doc_rag_retrieval")
    except Exception as error:
        message = f"문서 RAG 검색 실패: {error}"
        logger.exception(message)
        result["errors"].append(message)
    return result


def run_final_answer_step(
    *,
    question: str,
    planner_result: dict[str, Any] | None,
    generated_sql: str | None,
    db_result_summary: dict[str, Any] | None,
    rag_docs: list[dict[str, Any]] | None,
    config_path: str | Path | None = None,
    errors: list[str] | None = None,
) -> dict[str, Any]:
    """기존 결과를 종합해 최종 자연어 답변을 생성한다."""
    runtime = build_e2e_runtime(config_path=config_path)
    safe_rag_docs = rag_docs or []
    safe_errors = errors or []

    planner_text = json.dumps(planner_result or {}, ensure_ascii=False, indent=2)
    rag_preview = _build_rag_preview(safe_rag_docs, max_docs=4, max_chars=500)
    db_summary_text = (db_result_summary or {}).get("summary_text", "DB 요약 없음")
    sql_text = generated_sql or "생성 SQL 없음"
    error_text = "\n".join(safe_errors) if safe_errors else "오류 없음"

    system_prompt = (
        "당신은 한국어로 답변하는 분석 도우미다.\n"
        "아래에 이미 생성된 Planner/SQL/DB/RAG 결과를 종합해서 사용자 질문에 답하라.\n"
        "절대 SQL을 새로 생성하거나 실행하려고 하지 말고, 제공된 정보만 근거로 답하라.\n"
        "근거가 부족하면 부족하다고 명확히 밝히고, 필요한 추가 데이터도 짧게 제시하라."
    )
    user_prompt = (
        f"[사용자 질문]\n{question}\n\n"
        f"[Planner 결과]\n{planner_text}\n\n"
        f"[생성된 SQL]\n{sql_text}\n\n"
        f"[DB 결과 요약]\n{db_summary_text}\n\n"
        f"[문서 RAG 결과]\n{rag_preview}\n\n"
        f"[중간 오류]\n{error_text}\n\n"
        "위 결과를 종합해 최종 한국어 답변을 작성해줘."
    )

    try:
        final_answer = runtime.llm_client.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.2,
        ).strip()
        return {"final_answer": final_answer, "errors": []}
    except Exception as error:
        message = f"최종 답변 생성 실패: {error}"
        logger.exception(message)
        fallback_answer = _build_fallback_final_answer(
            question=question,
            db_result_summary=db_result_summary,
            rag_docs=safe_rag_docs,
            errors=[*safe_errors, message],
        )
        return {"final_answer": fallback_answer, "errors": [message]}


def run_end_to_end_planner_flow(
    *,
    question: str,
    config_path: str | Path | None = None,
    use_mock_db_result: bool = False,
    use_doc_rag: bool = True,
    doc_rag_top_k: int | None = None,
    mock_db_rows: list[dict[str, Any]] | None = None,
    sql_generation_mode: str | None = None,
) -> dict[str, Any]:
    """Planner -> DB -> RAG -> Final Answer를 순차 실행해 전체 결과를 반환한다."""
    clean_question = question.strip()
    if not clean_question:
        raise ValueError("질문이 비어 있습니다.")

    result: dict[str, Any] = {
        "question": clean_question,
        "planner_raw": None,
        "planner_result": None,
        "query_type": None,
        "reasoning_summary": None,
        "generated_sql": None,
        "sql_validation_result": None,
        "db_rows": [],
        "db_result_summary": None,
        "rag_query": None,
        "rag_docs": [],
        "final_answer": None,
        "selected_sql_mode": None,
        "executed_steps": [],
        "errors": [],
    }

    planner_out = run_planner_step(question=clean_question, config_path=config_path)
    result["planner_raw"] = planner_out["planner_raw"]
    result["planner_result"] = planner_out["planner_result"]
    result["query_type"] = planner_out["query_type"]
    result["reasoning_summary"] = planner_out["reasoning_summary"]
    result["executed_steps"].append("planner")

    db_out = run_db_step(
        question=clean_question,
        query_type=str(result["query_type"]),
        planner_steps=(result["planner_result"] or {}).get("steps", []),
        config_path=config_path,
        use_mock_db_result=use_mock_db_result,
        mock_db_rows=mock_db_rows,
        sql_generation_mode=sql_generation_mode,
    )
    result["generated_sql"] = db_out["generated_sql"]
    result["selected_sql_mode"] = db_out["selected_sql_mode"]
    result["sql_validation_result"] = db_out["sql_validation_result"]
    result["db_rows"] = db_out["db_rows"]
    result["db_result_summary"] = db_out["db_result_summary"]
    result["executed_steps"].extend(db_out["executed_steps"])
    result["errors"].extend(db_out["errors"])

    rag_out = run_doc_rag_step(
        question=clean_question,
        query_type=str(result["query_type"]),
        db_result_summary=result["db_result_summary"],
        config_path=config_path,
        use_doc_rag=use_doc_rag,
        doc_rag_top_k=doc_rag_top_k,
    )
    result["rag_query"] = rag_out["rag_query"]
    result["rag_docs"] = rag_out["rag_docs"]
    result["executed_steps"].extend(rag_out["executed_steps"])
    result["errors"].extend(rag_out["errors"])

    final_out = run_final_answer_step(
        question=clean_question,
        planner_result=result["planner_result"],
        generated_sql=result["generated_sql"],
        db_result_summary=result["db_result_summary"],
        rag_docs=result["rag_docs"],
        config_path=config_path,
        errors=result["errors"],
    )
    result["final_answer"] = final_out["final_answer"]
    result["errors"].extend(final_out["errors"])
    result["executed_steps"].append("final_answer")
    return result


def _extract_reasoning_summary(raw_response: str) -> str | None:
    """Planner raw JSON에서 reasoning_summary 필드가 있으면 추출한다."""
    try:
        payload = json.loads(raw_response)
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    value = payload.get("reasoning_summary")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _select_sql_generation_mode(
    *,
    query_type: str,
    planner_steps: list[dict[str, Any]],
    explicit_mode: str | None,
) -> str:
    """DB SQL 생성 시 prompt/rag_prompt 모드를 보수적으로 선택한다."""
    if explicit_mode:
        normalized = explicit_mode.strip().lower()
        if normalized not in {"prompt", "rag_prompt", "prompt_llm", "rag_prompt_llm"}:
            raise ValueError(f"지원하지 않는 sql_generation_mode 입니다: {explicit_mode}")
        if normalized.startswith("rag_prompt"):
            return "rag_prompt"
        return "prompt"

    if query_type == "DB_THEN_RAG":
        return "rag_prompt"

    for step in planner_steps:
        if str(step.get("type", "")).lower() == "rag":
            return "rag_prompt"
    return "prompt"


def _resolve_doc_retrieval_config(
    *,
    config: dict[str, Any],
    project_root: Path,
    doc_rag_top_k: int | None,
) -> dict[str, Any]:
    """doc_retrieval 설정을 우선 사용하고, 없으면 data_rag/rag_chunks 기본값으로 보정한다."""
    doc_cfg = config.get("doc_retrieval")
    if isinstance(doc_cfg, dict) and doc_cfg:
        embedding_model = str(
            doc_cfg.get(
                "embedding_model",
                "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            )
        )
        chroma_path = resolve_path(
            str(doc_cfg.get("chroma_path", "../Root_Ingest/data_rag/chroma")),
            project_root,
        )
        collection_name = str(doc_cfg.get("collection_name", "rag_chunks"))
        top_k = int(doc_cfg.get("top_k", 4))
        source = "doc_retrieval"
    else:
        retrieval_cfg = config.get("retrieval", {}) if isinstance(config.get("retrieval"), dict) else {}
        embedding_model = str(
            retrieval_cfg.get(
                "embedding_model",
                "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            )
        )
        chroma_path = resolve_path("../Root_Ingest/data_rag/chroma", project_root)
        collection_name = "rag_chunks"
        top_k = 4
        source = "fallback_default"

    if doc_rag_top_k is not None:
        top_k = max(1, int(doc_rag_top_k))

    return {
        "source": source,
        "embedding_model": embedding_model,
        "chroma_path": str(chroma_path),
        "collection_name": collection_name,
        "top_k": top_k,
    }


def _build_doc_rag_query(
    *,
    question: str,
    query_type: str,
    db_result_summary: dict[str, Any] | None,
) -> str:
    """DB_THEN_RAG일 때 DB 요약을 덧붙여 문서 검색 질의를 보강한다."""
    if query_type != "DB_THEN_RAG":
        return question

    summary_text = (db_result_summary or {}).get("summary_text")
    if not isinstance(summary_text, str) or not summary_text.strip():
        return question
    return f"{question}\n\n[DB 결과 요약]\n{summary_text}"


def _build_rag_preview(rag_docs: list[dict[str, Any]], *, max_docs: int, max_chars: int) -> str:
    """최종 답변 생성용으로 RAG 문서를 짧게 압축한다."""
    if not rag_docs:
        return "RAG 검색 결과 없음"

    lines: list[str] = []
    for index, doc in enumerate(rag_docs[:max_docs], start=1):
        metadata = doc.get("metadata", {}) if isinstance(doc, dict) else {}
        source_name = metadata.get("source") if isinstance(metadata, dict) else None
        chunk_id = doc.get("chunk_id", f"unknown_{index}") if isinstance(doc, dict) else f"unknown_{index}"
        score = doc.get("score") if isinstance(doc, dict) else None
        text = str(doc.get("text", "")) if isinstance(doc, dict) else ""
        text = text.replace("\n", " ").strip()
        if len(text) > max_chars:
            text = text[:max_chars] + "..."
        lines.append(
            f"[{index}] chunk_id={chunk_id}, source={source_name}, score={score}\n{text}"
        )
    return "\n\n".join(lines)


def _default_mock_db_rows() -> list[dict[str, Any]]:
    """DB 미연결 상태에서 흐름 점검용 기본 mock 데이터를 반환한다."""
    return [
        {"eqpid": "EQP-01", "error_count": 12, "latest_event_time": "2026-04-08 13:21:00"},
        {"eqpid": "EQP-03", "error_count": 8, "latest_event_time": "2026-04-08 12:54:10"},
        {"eqpid": "EQP-07", "error_count": 4, "latest_event_time": "2026-04-08 11:40:09"},
    ]


def _build_fallback_final_answer(
    *,
    question: str,
    db_result_summary: dict[str, Any] | None,
    rag_docs: list[dict[str, Any]],
    errors: list[str],
) -> str:
    """LLM 호출 실패 시 노트북 검증을 계속할 수 있도록 최소 대체 답변을 만든다."""
    lines = [f"질문: {question}", "", "[자동 fallback 응답]"]
    if db_result_summary:
        lines.append("- DB 요약:")
        lines.append(str(db_result_summary.get("summary_text", "요약 없음")))
    else:
        lines.append("- DB 요약 없음")

    if rag_docs:
        lines.append(f"- RAG 문서 {len(rag_docs)}건 검색됨")
    else:
        lines.append("- RAG 문서 검색 결과 없음")

    if errors:
        lines.append("- 오류:")
        for item in errors[-3:]:
            lines.append(f"  - {item}")
    return "\n".join(lines)
