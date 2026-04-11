# 이 파일은 ChunkItem 목록을 받아 임베딩 벡터를 생성하는 4단계 담당이다.
# SentenceTransformer 모델로 배치 처리해 임베딩 속도를 높인다.
# config.retrieval.embedding_model 값으로 모델을 선택하며 교체가 쉽다.
# 생성된 EmbeddingItem은 vector_store_service.py에 전달해 Chroma에 저장한다.

from __future__ import annotations

from typing import Any

from src.db_to_llm.ingest.models import ChunkItem, EmbeddingItem
from src.db_to_llm.shared.logging.logger import get_logger

logger = get_logger(__name__)

# SentenceTransformer는 무거운 라이브러리라 실제 필요 시점에만 import
_sentence_transformer_cache: dict[str, Any] = {}


def create_embeddings(
    chunks: list[ChunkItem],
    embedding_model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    batch_size: int = 32,
    normalize: bool = True,
) -> list[EmbeddingItem]:
    """
    ChunkItem 목록을 임베딩해 EmbeddingItem 목록을 반환한다.

    Args:
        chunks: 3단계(chunk_documents)에서 생성한 청크 목록.
        embedding_model_name: SentenceTransformer 모델 이름.
        batch_size: 배치 처리 크기. 메모리에 따라 조절한다.
        normalize: 임베딩 벡터를 정규화할지 여부.

    Returns:
        list[EmbeddingItem]: 임베딩 벡터가 포함된 아이템 목록.
    """
    logger.info(
        "임베딩 시작: total_chunks=%d, model=%s",
        len(chunks),
        embedding_model_name,
    )

    model = _load_sentence_transformer(embedding_model_name)

    # 텍스트만 추출해 배치 임베딩
    texts = [chunk.chunk_text for chunk in chunks]

    try:
        vectors = model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=normalize,
            show_progress_bar=False,
        )
    except Exception:
        logger.exception("임베딩 생성 실패: model=%s", embedding_model_name)
        raise

    embedding_items: list[EmbeddingItem] = []
    for chunk, vector in zip(chunks, vectors):
        item = EmbeddingItem(
            chunk_id=chunk.chunk_id,
            parent_document_id=chunk.parent_document_id,
            source_path=chunk.source_path,
            chunk_text=chunk.chunk_text,
            embedding=vector.tolist(),
            metadata=chunk.metadata,
        )
        embedding_items.append(item)

    logger.info("임베딩 완료: total=%d", len(embedding_items))
    return embedding_items


def _load_sentence_transformer(model_name: str) -> Any:
    """
    SentenceTransformer 모델을 로드한다.
    이미 로드된 모델은 캐시에서 반환해 중복 로딩을 피한다.

    Args:
        model_name: 로드할 모델 이름.

    Returns:
        SentenceTransformer 모델 인스턴스.

    Raises:
        ImportError: sentence-transformers 패키지가 없는 경우 발생한다.
    """
    if model_name in _sentence_transformer_cache:
        return _sentence_transformer_cache[model_name]

    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as error:
        raise ImportError(
            "sentence-transformers 패키지가 없습니다. "
            "`pip install sentence-transformers`로 설치하세요."
        ) from error

    logger.info("SentenceTransformer 모델 로드 시작: %s", model_name)
    model = SentenceTransformer(model_name)
    _sentence_transformer_cache[model_name] = model
    logger.info("SentenceTransformer 모델 로드 완료: %s", model_name)
    return model
