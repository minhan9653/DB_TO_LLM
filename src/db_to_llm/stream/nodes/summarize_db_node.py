# 이 파일은 DB 조회 결과 rows를 LLM으로 요약하는 노드이다.
# row 전체를 그대로 LLM에 넣지 않고 샘플(최대 20행)과 통계를 정리해 넣는다.
# DB_THEN_RAG 경로에서는 요약된 db_summary가 RAG 검색 쿼리 확장에 활용된다.
# 요약 결과는 db_summary에 저장되고 final_answer_node에서 최종 답변 생성에 사용된다.

from __future__ import annotations

import json

from src.db_to_llm.shared.logging.logger import get_logger
from src.db_to_llm.stream.graph.state import GraphState
from src.db_to_llm.stream.nodes.node_helpers import append_error, append_trace, get_config
from src.db_to_llm.stream.services.llm_service import generate_text
from src.db_to_llm.stream.services.prompt_service import get_prompt_manager

logger = get_logger(__name__)

# 요약용 LLM에 전달할 최대 샘플 행 수
MAX_SAMPLE_ROWS = 20


def summarize_db_node(state: GraphState) -> GraphState:
    """
    DB 조회 결과를 LLM으로 요약해 db_summary에 저장한다.

    입력 state 키: db_rows, db_columns, db_row_count
    출력 state 키: db_summary

    Args:
        state: 현재 그래프 실행 상태.

    Returns:
        GraphState: db_summary가 추가된 상태.
    """
    db_rows = state.get("db_rows", [])
    db_columns = state.get("db_columns", [])
    db_row_count = state.get("db_row_count", 0)

    # 결과가 없으면 요약 스킵
    if not db_rows:
        logger.info("summarize_db_node: DB 결과가 없어 요약을 건너뜁니다.")
        return {
            **state,
            "db_summary": None,
            "trace_logs": append_trace(state, "summarize_db_node: DB 결과 없음"),
        }

    logger.info("summarize_db_node 시작: row_count=%d", db_row_count)

    config = get_config(state)
    prompt_manager = get_prompt_manager(config)

    # 샘플 데이터 준비 (LLM 컨텍스트 초과 방지를 위해 최대 20행만 사용)
    sample_rows = db_rows[:MAX_SAMPLE_ROWS]
    sample_rows_text = json.dumps(sample_rows, ensure_ascii=False, indent=2)
    columns_text = ", ".join(db_columns)

    try:
        user_prompt = prompt_manager.render_prompt(
            "db_result_summary_prompt",
            values={
                "row_count": str(db_row_count),
                "columns": columns_text,
                "sample_rows": sample_rows_text,
            },
        )

        system_prompt = "너는 데이터베이스 조회 결과를 분석하고 한국어로 간결하게 요약하는 전문가다."

        db_summary = generate_text(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            config=config,
            caller_name="summarize_db_node",
        )

        logger.info("summarize_db_node 완료: summary_length=%d", len(db_summary))

        return {
            **state,
            "db_summary": db_summary,
            "trace_logs": append_trace(
                state, f"summarize_db_node: summary_length={len(db_summary)}"
            ),
        }

    except Exception as error:
        logger.error("summarize_db_node 실패: %s", error)
        # 요약 실패 시 첫 5행을 문자열로 변환해 사용
        fallback_summary = f"DB 조회 결과 {db_row_count}행. 컬럼: {columns_text}"
        return {
            **state,
            "db_summary": fallback_summary,
            "errors": append_error(state, f"summarize_db_node 실패: {error}"),
            "trace_logs": append_trace(state, "summarize_db_node: 실패, fallback 사용"),
        }
