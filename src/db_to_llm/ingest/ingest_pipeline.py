# 이 파일은 ingest 전 단계(수집→파싱→청킹→임베딩→저장)를 하나로 연결하는 파이프라인이다.
# config.yaml의 ingest 섹션 설정을 읽어 각 단계 서비스를 순서대로 호출한다.
# 중간 결과를 JSONL로 저장해 노트북에서 단계별로 확인하고 재실행할 수 있다.
# 이 파일을 직접 실행하거나 노트북에서 import해 파이프라인을 돌릴 수 있다.

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from src.db_to_llm.ingest.chunk_service import chunk_documents, save_chunks_to_jsonl
from src.db_to_llm.ingest.document_loader import collect_documents, save_documents_to_jsonl
from src.db_to_llm.ingest.embedding_service import create_embeddings
from src.db_to_llm.ingest.parser_service import parse_documents, save_parsed_documents
from src.db_to_llm.ingest.vector_store_service import upsert_embeddings_to_chroma
from src.db_to_llm.shared.config.config_loader import load_config
from src.db_to_llm.shared.logging.logger import get_logger, setup_logger

logger = get_logger(__name__)


def run_ingest_pipeline(config_path: Path | None = None) -> dict[str, Any]:
    """
    ingest 파이프라인 전체를 실행한다.
    수집 → 파싱 → 청킹 → 임베딩 → ChromaDB 저장 순서로 실행된다.

    Args:
        config_path: 설정 파일 경로. None이면 config/config.yaml을 사용한다.

    Returns:
        dict: 각 단계의 처리 결과 통계.
    """
    config = load_config(config_path)

    # 로깅 설정
    log_level = config.get("logging", {}).get("level", "INFO")
    log_file = config.get("logging", {}).get("log_file")
    log_file_path = Path(log_file) if log_file else None
    setup_logger(log_level=log_level, log_file_path=log_file_path)

    logger.info("=" * 60)
    logger.info("Ingest 파이프라인 시작")

    ingest_config = config.get("ingest", {})
    project_root = Path.cwd()

    doc_dir = project_root / ingest_config.get("doc_dir", "data/doc")
    output_dir = project_root / ingest_config.get("output_dir", "data/ingest_output")
    supported_extensions = ingest_config.get(
        "supported_extensions", [".pdf", ".docx", ".txt", ".md", ".sql"]
    )
    parser_name = ingest_config.get("parser", "simple")
    chunk_size = int(ingest_config.get("chunk_size", 800))
    chunk_overlap = int(ingest_config.get("chunk_overlap", 100))

    retrieval_config = config.get("retrieval", {})
    embedding_model = retrieval_config.get(
        "embedding_model",
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    )
    chroma_path = str(project_root / retrieval_config.get("chroma_path", "data/chroma"))
    collection_name = retrieval_config.get("collection_name", "doc_chunks")

    # ──────────────────────────────────────────
    # 1단계: 문서 수집
    # ──────────────────────────────────────────
    logger.info("[1단계] 문서 수집 시작")
    documents = collect_documents(doc_dir=doc_dir, supported_extensions=supported_extensions)
    save_documents_to_jsonl(documents, output_dir / "01_documents.jsonl")
    logger.info("[1단계] 문서 수집 완료: count=%d", len(documents))

    if not documents:
        logger.warning("수집된 문서가 없습니다. 파이프라인을 종료합니다.")
        return {"documents": 0, "parsed": 0, "chunks": 0, "embeddings": 0}

    # ──────────────────────────────────────────
    # 2단계: 텍스트 파싱
    # ──────────────────────────────────────────
    logger.info("[2단계] 문서 파싱 시작")
    parsed_documents = parse_documents(documents=documents, parser_name=parser_name)
    save_parsed_documents(parsed_documents, output_dir / "02_parsed.jsonl")
    logger.info("[2단계] 문서 파싱 완료: count=%d", len(parsed_documents))

    # ──────────────────────────────────────────
    # 3단계: 청킹
    # ──────────────────────────────────────────
    logger.info("[3단계] 청킹 시작")
    chunks = chunk_documents(
        parsed_documents=parsed_documents,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    save_chunks_to_jsonl(chunks, output_dir / "03_chunks.jsonl")
    logger.info("[3단계] 청킹 완료: count=%d", len(chunks))

    # ──────────────────────────────────────────
    # 4단계: 임베딩 생성
    # ──────────────────────────────────────────
    logger.info("[4단계] 임베딩 시작")
    embedding_items = create_embeddings(chunks=chunks, embedding_model_name=embedding_model)
    logger.info("[4단계] 임베딩 완료: count=%d", len(embedding_items))

    # ──────────────────────────────────────────
    # 5단계: ChromaDB 저장
    # ──────────────────────────────────────────
    logger.info("[5단계] ChromaDB 저장 시작")
    upsert_embeddings_to_chroma(
        embedding_items=embedding_items,
        chroma_path=chroma_path,
        collection_name=collection_name,
    )
    logger.info("[5단계] ChromaDB 저장 완료")

    logger.info("=" * 60)
    logger.info("Ingest 파이프라인 완료")

    return {
        "documents": len(documents),
        "parsed": len(parsed_documents),
        "chunks": len(chunks),
        "embeddings": len(embedding_items),
    }


if __name__ == "__main__":
    result = run_ingest_pipeline()
    print(f"파이프라인 완료: {result}")
