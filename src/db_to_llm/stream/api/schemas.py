# 이 파일은 API 요청/응답 Pydantic 스키마를 정의한다.
# FastAPI가 자동으로 입력 검증과 OpenAPI 문서를 생성하는 데 활용한다.
# 요청에는 question이 필수이고, 설정 파일 경로를 선택적으로 전달할 수 있다.
# 응답에는 최종 답변, query_type, SQL, DB/RAG 결과, 오류 정보가 포함된다.

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """POST /query 요청 스키마."""

    question: str = Field(..., description="사용자의 자연어 질문", min_length=1)
    config_path: str | None = Field(
        default=None,
        description="사용할 설정 파일 경로. 비워두면 config/config.yaml을 사용한다.",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "question": "지난달 매출 상위 10개 제품을 알려줘",
                "config_path": None,
            }
        }
    }


class QueryResponse(BaseModel):
    """POST /query 응답 스키마."""

    question: str = Field(..., description="입력된 질문")
    query_type: str = Field(..., description="Planner가 결정한 쿼리 유형")
    final_answer: str | None = Field(None, description="최종 사용자 답변")
    generated_sql: str | None = Field(None, description="생성된 SQL")
    validated_sql: str | None = Field(None, description="검증된 SQL")
    db_rows: list[dict[str, Any]] = Field(default_factory=list, description="DB 조회 결과")
    db_summary: str | None = Field(None, description="DB 결과 요약")
    retrieved_contexts: list[dict[str, Any]] = Field(
        default_factory=list, description="RAG 검색 결과"
    )
    errors: list[str] = Field(default_factory=list, description="처리 중 발생한 오류 목록")
    trace_logs: list[str] = Field(default_factory=list, description="단계별 처리 로그")
    planner_result: dict[str, Any] = Field(
        default_factory=dict, description="Planner가 생성한 실행 계획"
    )
