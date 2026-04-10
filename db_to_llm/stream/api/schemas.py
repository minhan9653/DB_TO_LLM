# 이 파일은 Stream API 계층에서 사용하는 요청/응답 스키마를 정의한다.
# Root_Stream.server와 신규 graph runner 사이 데이터 계약을 명확히 유지한다.
# Pydantic 모델을 통해 입력 검증과 문서화를 동시에 제공한다.
# 기존 API 응답 필드를 유지해 하위 클라이언트 호환성을 최대한 보존한다.

from __future__ import annotations

from pydantic import BaseModel, Field


class QueryGenerateRequest(BaseModel):
    """SQL 생성 요청 스키마."""

    question: str = Field(..., min_length=1, description="사용자 질문")
    mode: str = Field(default="prompt", description="auto|natural|prompt|rag_prompt")


class QueryGenerateResponse(BaseModel):
    """SQL 생성 응답 스키마."""

    success: bool
    mode: str | None
    question: str
    generated_query: str
    errors: list[str] = Field(default_factory=list)

