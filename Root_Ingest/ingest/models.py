# 이 파일은 단계별 데이터 형식을 dataclass로 정의합니다.

# 문서, 파싱 결과, 청크, 임베딩 형식을 공통 구조로 맞춥니다.

# 각 서비스 모듈은 이 모델을 사용해 입출력 형식을 통일합니다.

# Text-to-SQL RAG 재사용을 위해 메타데이터 필드를 유지합니다.

from __future__ import annotations
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass

class DocumentItem:
    """문서 수집 단계의 기본 메타데이터 모델입니다."""

    document_id: str

    source_path: str

    file_name: str

    file_type: str

    file_size: int

    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """
        역할:
        INGEST 모델 직렬화 객체를 JSON 직렬화 가능한 dict로 변환합니다.
        
        Returns:
        dict[str, Any]: INGEST 모델 직렬화 단계에서 후속 처리에 바로 사용할 매핑 데이터를 반환합니다.
        
        Raises:
        Exception: 명시적 raise가 없어도 파일 I/O, 네트워크, 외부 라이브러리 예외가 전파될 수 있습니다.
        """
        return asdict(self)


@dataclass

class ParsedDocument:
    """파싱 결과를 담는 공통 모델입니다."""

    document_id: str

    source_path: str

    file_type: str

    raw_text: str

    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """
        역할:
        INGEST 모델 직렬화 객체를 JSON 직렬화 가능한 dict로 변환합니다.
        
        Returns:
        dict[str, Any]: INGEST 모델 직렬화 단계에서 후속 처리에 바로 사용할 매핑 데이터를 반환합니다.
        
        Raises:
        Exception: 명시적 raise가 없어도 파일 I/O, 네트워크, 외부 라이브러리 예외가 전파될 수 있습니다.
        """
        return asdict(self)


@dataclass

class ChunkItem:
    """청킹 단계 결과를 저장하는 모델입니다."""

    chunk_id: str

    parent_document_id: str

    chunk_text: str

    chunk_index: int

    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """
        역할:
        INGEST 모델 직렬화 객체를 JSON 직렬화 가능한 dict로 변환합니다.
        
        Returns:
        dict[str, Any]: INGEST 모델 직렬화 단계에서 후속 처리에 바로 사용할 매핑 데이터를 반환합니다.
        
        Raises:
        Exception: 명시적 raise가 없어도 파일 I/O, 네트워크, 외부 라이브러리 예외가 전파될 수 있습니다.
        """
        return asdict(self)


@dataclass

class EmbeddingItem:
    """임베딩 생성 결과를 저장하는 모델입니다."""

    chunk_id: str

    parent_document_id: str

    chunk_text: str

    embedding: list[float]

    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """
        역할:
        INGEST 모델 직렬화 객체를 JSON 직렬화 가능한 dict로 변환합니다.
        
        Returns:
        dict[str, Any]: INGEST 모델 직렬화 단계에서 후속 처리에 바로 사용할 매핑 데이터를 반환합니다.
        
        Raises:
        Exception: 명시적 raise가 없어도 파일 I/O, 네트워크, 외부 라이브러리 예외가 전파될 수 있습니다.
        """
        return asdict(self)
