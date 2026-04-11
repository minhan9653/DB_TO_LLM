# 이 파일은 ParsedDocument를 받아 일정 크기로 잘라 ChunkItem을 생성하는 3단계 담당이다.
# chunk_size(글자 수)와 chunk_overlap(겹치는 글자 수)으로 청킹 방법을 조절한다.
# chunk_id는 parent_document_id + 인덱스로 생성해 원본과의 추적 관계를 유지한다.
# 생성된 ChunkItem은 embedding_service.py에 전달해 임베딩 단계로 이어진다.

from __future__ import annotations

import json
from pathlib import Path

from src.db_to_llm.ingest.models import ChunkItem, ParsedDocument
from src.db_to_llm.shared.logging.logger import get_logger

logger = get_logger(__name__)


def chunk_documents(
    parsed_documents: list[ParsedDocument],
    chunk_size: int = 800,
    chunk_overlap: int = 100,
) -> list[ChunkItem]:
    """
    ParsedDocument 목록을 받아 지정된 크기로 청킹해 ChunkItem 목록을 반환한다.

    Args:
        parsed_documents: 2단계(parse_documents)에서 추출한 파싱 결과 목록.
        chunk_size: 각 청크의 최대 글자 수. 기본값 800.
        chunk_overlap: 연속된 청크 간 겹치는 글자 수. 기본값 100.

    Returns:
        list[ChunkItem]: 청킹된 텍스트 조각 목록.
    """
    logger.info(
        "청킹 시작: total_docs=%d, chunk_size=%d, overlap=%d",
        len(parsed_documents),
        chunk_size,
        chunk_overlap,
    )

    all_chunks: list[ChunkItem] = []

    for parsed in parsed_documents:
        chunks = split_text_by_char_count(
            text=parsed.raw_text,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        for index, chunk_text in enumerate(chunks):
            chunk_id = f"{parsed.document_id}_chunk_{index:04d}"
            chunk = ChunkItem(
                chunk_id=chunk_id,
                parent_document_id=parsed.document_id,
                source_path=parsed.source_path,
                file_type=parsed.file_type,
                chunk_text=chunk_text,
                chunk_index=index,
                metadata={
                    "file_name": parsed.metadata.get("file_name", ""),
                    "char_count": len(chunk_text),
                },
            )
            all_chunks.append(chunk)

        logger.info(
            "청킹 완료: doc_id=%s, chunk_count=%d",
            parsed.document_id[:8],
            len(chunks),
        )

    logger.info("전체 청킹 완료: total_chunks=%d", len(all_chunks))
    return all_chunks


def split_text_by_char_count(
    text: str,
    chunk_size: int,
    chunk_overlap: int,
) -> list[str]:
    """
    텍스트를 글자 수 기준으로 잘라 청크 목록을 반환한다.
    빈 텍스트는 빈 리스트를 반환한다.

    Args:
        text: 분할할 전체 텍스트.
        chunk_size: 각 청크의 최대 글자 수.
        chunk_overlap: 앞 청크와 겹치는 글자 수.

    Returns:
        list[str]: 분할된 텍스트 청크 목록.
    """
    if not text.strip():
        return []

    step = max(1, chunk_size - chunk_overlap)
    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += step

    return chunks


def save_chunks_to_jsonl(chunks: list[ChunkItem], output_path: Path) -> None:
    """
    ChunkItem 목록을 JSONL 형식으로 저장한다.

    Args:
        chunks: 저장할 청크 목록.
        output_path: 저장할 JSONL 파일 경로.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        for chunk in chunks:
            file.write(json.dumps(chunk.to_dict(), ensure_ascii=False) + "\n")
    logger.info("청크 저장 완료: path=%s, count=%d", output_path, len(chunks))
