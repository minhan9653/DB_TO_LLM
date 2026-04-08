# 이 파일은 STREAM 서버의 요청/응답 스키마를 정의합니다.
# FastAPI 라우트에서 검증과 문서화를 단순하게 유지하기 위해 분리했습니다.
# 실제 SQL 생성 로직은 services/query_service.py 에서 처리합니다.
# 초보자도 구조를 따라가기 쉽게 최소 필드만 유지합니다.

from __future__ import annotations

from pydantic import BaseModel, Field


class QueryGenerateRequest(BaseModel):
    """POST /api/query/generate 요청 본문 모델입니다."""

    question: str = Field(..., min_length=1, description="사용자 질문")
    mode: str = Field(
        default="prompt",
        description="natural | prompt | rag_prompt (또는 내부 mode 명)",
    )


class QueryGenerateResponse(BaseModel):
    """POST /api/query/generate 응답 모델입니다."""

    success: bool = Field(..., description="요청 성공 여부")
    mode: str = Field(..., description="적용된 mode")
    question: str = Field(..., description="입력 질문")
    generated_query: str = Field(..., description="생성된 SQL")
