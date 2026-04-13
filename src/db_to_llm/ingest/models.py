# 이 파일은 ingest 파이프라인의 각 단계에서 사용하는 데이터 모델을 정의한다.
# DocumentItem, ParsedDocument, ChunkItem, EmbeddingItem 4가지 모델이 있다.
# 각 서비스 모듈은 이 모델을 사용해 입출력 형식을 통일한다.
# JSONL 직렬화를 위해 to_dict() 메서드를 모든 모델에 제공한다.

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class DocumentItem:
    """문서 수집 단계의 기본 메타데이터 모델."""

    document_id: str           # 파일 경로 기반 해시 ID
    source_path: str           # 원본 파일 경로
    file_name: str             # 파일명
    file_type: str             # 확장자 (.pdf, .docx 등)
    file_size: int             # 파일 크기 (바이트)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """JSON 직렬화 가능한 dict로 변환한다."""
        return asdict(self)


@dataclass
class ParsedDocument:
    """파서가 문서에서 추출한 텍스트와 메타데이터를 담는 모델."""

    document_id: str           # 원본 DocumentItem의 ID
    source_path: str           # 원본 파일 경로
    file_type: str             # 확장자
    raw_text: str              # 추출된 전체 텍스트
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """JSON 직렬화 가능한 dict로 변환한다."""
        return asdict(self)


@dataclass
class ChunkItem:
    """청킹 단계에서 생성된 텍스트 조각 모델."""

    chunk_id: str              # parent_document_id_chunk_XXXX 형식
    parent_document_id: str   # 원본 문서 ID
    source_path: str           # 원본 파일 경로
    file_type: str             # 확장자
    chunk_text: str            # 청크 텍스트
    chunk_index: int           # 청크 순서 (0부터 시작)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """JSON 직렬화 가능한 dict로 변환한다."""
        return asdict(self)


@dataclass
class EmbeddingItem:
    """임베딩 단계에서 생성된 벡터와 메타데이터를 담는 모델."""

    chunk_id: str              # ChunkItem의 ID
    parent_document_id: str   # 원본 문서 ID
    source_path: str           # 원본 파일 경로
    chunk_text: str            # 임베딩된 텍스트
    embedding: list[float]     # 임베딩 벡터
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """JSON 직렬화 가능한 dict로 변환한다. 임베딩 벡터는 제외한다."""
        result = asdict(self)
        result.pop("embedding", None)  # 벡터는 JSONL에 저장하지 않음
        return result
