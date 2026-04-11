# 이 파일은 LangGraph 노드들이 공유하는 상태(State)를 정의한다.
# 모든 노드는 이 상태를 입력으로 받고 업데이트된 상태를 반환한다.
# 각 필드가 어느 노드에서 채워지는지 주석으로 명시해 흐름 추적을 쉽게 한다.
# TypedDict를 사용해 dict처럼 다루면서도 타입 힌트의 이점을 얻는다.

from __future__ import annotations

from typing import Any, TypedDict


class GraphState(TypedDict, total=False):
    """LangGraph 노드 간에 공유되는 전체 실행 상태."""

    # ── 입력 ──────────────────────────────────────────────
    question: str                        # 사용자 원본 질문
    config_path: str                     # 설정 파일 경로 (선택)

    # ── Planner 결과 ──────────────────────────────────────
    # planner_node가 채운다.
    planner_result: dict[str, Any]       # PlannerPlan.to_dict() 결과
    query_type: str                      # DB_ONLY | RAG_ONLY | GENERAL | ...
    planner_steps: list[dict[str, Any]]  # PlannerStep 목록

    # ── SQL 생성 ──────────────────────────────────────────
    # generate_sql_node가 채운다.
    generated_sql: str | None            # LLM이 생성한 SQL (검증 전)

    # ── SQL 검증 ──────────────────────────────────────────
    # validate_sql_node가 채운다.
    validated_sql: str | None            # 검증 통과한 SQL
    sql_validation_passed: bool          # 검증 통과 여부
    sql_validation_error: str | None     # 검증 실패 상세 메시지

    # ── DB 실행 ──────────────────────────────────────────
    # execute_sql_node가 채운다.
    db_rows: list[dict[str, Any]]        # DB 조회 결과 행 목록
    db_columns: list[str]                # 조회된 컬럼명 목록
    db_row_count: int                    # 조회된 행 수

    # ── DB 결과 요약 ─────────────────────────────────────
    # summarize_db_node가 채운다.
    db_summary: str | None               # DB 결과를 LLM으로 요약한 텍스트

    # ── RAG 검색 ──────────────────────────────────────────
    # retrieve_rag_node가 채운다.
    retrieved_contexts: list[dict[str, Any]]  # 검색된 문서 청크 목록

    # ── 최종 답변 ─────────────────────────────────────────
    # final_answer_node 또는 general_answer_node가 채운다.
    final_answer: str | None             # 사용자에게 전달할 최종 답변

    # ── 디버그 / 오류 추적 ────────────────────────────────
    errors: list[str]                    # 단계별 오류 메시지 목록
    trace_logs: list[str]                # 단계별 처리 로그 목록

    # ── 테스트 전용 ──────────────────────────────────────
    # 단위/통합 테스트에서 실제 파일 로딩 없이 config를 직접 주입할 때만 사용한다.
    # node_helpers.get_config()가 config_path보다 이 값을 우선한다.
    _config_override: dict  # 테스트 픽스처에서 주입하는 설정 dict
