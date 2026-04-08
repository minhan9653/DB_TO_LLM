# 이 파일은 STREAM 단계의 입력/출력 데이터 구조를 dataclass로 정의합니다.

# mode가 달라도 동일한 결과 포맷(StreamResult)을 반환하도록 강제합니다.

# RAG 검색 컨텍스트도 별도 모델로 분리해 가독성과 확장성을 높입니다.

# 노트북/CLI/서비스가 공통 모델을 사용하도록 연결하는 역할을 합니다.

from __future__ import annotations
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass

class StreamRequest:
    """STREAM 실행 입력 모델입니다."""

    question: str

    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """
        역할:
        STREAM 모델 직렬화 객체를 JSON 직렬화 가능한 dict로 변환합니다.
        
        Returns:
        dict[str, Any]: STREAM 모델 직렬화 단계에서 후속 처리에 바로 사용할 매핑 데이터를 반환합니다.
        
        Raises:
        Exception: 명시적 raise가 없어도 파일 I/O, 네트워크, 외부 라이브러리 예외가 전파될 수 있습니다.
        """
        return asdict(self)


@dataclass

class RetrievedContext:
    """RAG 검색으로 찾은 컨텍스트 모델입니다."""

    chunk_id: str

    text: str

    score: float | None = None

    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """
        역할:
        STREAM 모델 직렬화 객체를 JSON 직렬화 가능한 dict로 변환합니다.
        
        Returns:
        dict[str, Any]: STREAM 모델 직렬화 단계에서 후속 처리에 바로 사용할 매핑 데이터를 반환합니다.
        
        Raises:
        Exception: 명시적 raise가 없어도 파일 I/O, 네트워크, 외부 라이브러리 예외가 전파될 수 있습니다.
        """
        return asdict(self)


@dataclass

class StreamResult:
    """모든 STREAM mode가 공통으로 반환하는 결과 모델입니다."""

    mode: str

    question: str

    query: str

    llm_provider: str | None = None

    prompt_key: str | None = None

    retrieved_contexts: list[RetrievedContext] = field(default_factory=list)

    raw_response: Any = None

    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """
        역할:
        STREAM 모델 직렬화 객체를 JSON 직렬화 가능한 dict로 변환합니다.
        
        Returns:
        dict[str, Any]: STREAM 모델 직렬화 단계에서 후속 처리에 바로 사용할 매핑 데이터를 반환합니다.
        
        Raises:
        Exception: 명시적 raise가 없어도 파일 I/O, 네트워크, 외부 라이브러리 예외가 전파될 수 있습니다.
        """

        payload = asdict(self)

        payload["retrieved_contexts"] = [item.to_dict() for item in self.retrieved_contexts]
        return payload
