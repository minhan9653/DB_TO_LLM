# 이 파일은 EmbeddingItem을 받아 ChromaDB에 저장하는 5단계 담당이다.
# persistent 모드로 저장해 ingest 후 stream에서 재사용할 수 있게 한다.
# upsert 방식으로 중복 chunk_id는 덮어쓰고 신규는 추가한다.
# retrieve_rag_node에서 이 Chroma 컬렉션을 조회해 RAG 검색을 수행한다.

from __future__ import annotations

from typing import Any

from src.db_to_llm.ingest.models import EmbeddingItem
from src.db_to_llm.shared.logging.logger import get_logger

logger = get_logger(__name__)

# ChromaDB는 무거운 라이브러리라 실제 필요 시점에만 import
_chroma_client_cache: dict[str, Any] = {}


def upsert_embeddings_to_chroma(
    embedding_items: list[EmbeddingItem],
    chroma_path: str,
    collection_name: str,
    batch_size: int = 100,
) -> None:
    """
    EmbeddingItem 목록을 ChromaDB에 upsert한다.
    이미 같은 chunk_id가 있으면 업데이트하고 없으면 추가한다.

    Args:
        embedding_items: 4단계(create_embeddings)에서 생성한 임베딩 목록.
        chroma_path: Chroma 데이터 저장 경로. config.retrieval.chroma_path.
        collection_name: Chroma 컬렉션 이름. config.retrieval.collection_name.
        batch_size: 한 번에 upsert할 최대 아이템 수.
    """
    logger.info(
        "ChromaDB upsert 시작: total=%d, path=%s, collection=%s",
        len(embedding_items),
        chroma_path,
        collection_name,
    )

    collection = _get_or_create_collection(chroma_path, collection_name)

    # 배치 단위로 upsert
    for batch_start in range(0, len(embedding_items), batch_size):
        batch = embedding_items[batch_start: batch_start + batch_size]

        ids = [item.chunk_id for item in batch]
        embeddings = [item.embedding for item in batch]
        documents = [item.chunk_text for item in batch]
        metadatas = [_sanitize_metadata(item.metadata) for item in batch]

        try:
            collection.upsert(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
            )
            logger.info("배치 upsert 완료: batch_start=%d, size=%d", batch_start, len(batch))
        except Exception:
            logger.exception("ChromaDB upsert 실패: batch_start=%d", batch_start)
            raise

    logger.info("ChromaDB upsert 전체 완료: total=%d", len(embedding_items))


def sample_from_collection(
    chroma_path: str,
    collection_name: str,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """
    Chroma 컬렉션에서 샘플 문서를 가져와 저장 상태를 확인한다.

    Args:
        chroma_path: Chroma 데이터 저장 경로.
        collection_name: 컬렉션 이름.
        limit: 가져올 샘플 수.

    Returns:
        list[dict]: 샘플 문서 목록.
    """
    collection = _get_or_create_collection(chroma_path, collection_name)
    result = collection.peek(limit=limit)
    samples = []
    for i, doc_id in enumerate(result.get("ids", [])):
        samples.append({
            "id": doc_id,
            "document": result.get("documents", [])[i] if result.get("documents") else "",
            "metadata": result.get("metadatas", [])[i] if result.get("metadatas") else {},
        })
    return samples


def _get_or_create_collection(chroma_path: str, collection_name: str) -> Any:
    """Chroma 클라이언트와 컬렉션을 가져오거나 생성한다."""
    cache_key = f"{chroma_path}::{collection_name}"
    if cache_key in _chroma_client_cache:
        return _chroma_client_cache[cache_key]

    try:
        import chromadb
    except ImportError as error:
        raise ImportError(
            "chromadb 패키지가 없습니다. `pip install chromadb`로 설치하세요."
        ) from error

    client = chromadb.PersistentClient(path=chroma_path)
    collection = client.get_or_create_collection(name=collection_name)
    _chroma_client_cache[cache_key] = collection
    logger.info("Chroma 컬렉션 준비 완료: %s", collection_name)
    return collection


def _sanitize_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Chroma가 허용하는 타입(str, int, float, bool)으로 메타데이터를 정리한다."""
    sanitized: dict[str, Any] = {}
    for key, value in metadata.items():
        if isinstance(value, (str, int, float, bool)):
            sanitized[key] = value
        else:
            sanitized[key] = str(value)
    return sanitized
