# 이 파일은 ChromaDB에서 관련 문서를 검색하는 RAG 검색 서비스를 담는다.
# 질문(또는 질문+DB요약)을 임베딩해 Chroma 컬렉션에서 가장 유사한 청크를 찾는다.
# retrieve_rag_node에서 호출하며, DB_THEN_RAG 경로에서는 db_summary도 함께 활용한다.
# 검색 결과는 retrieved_contexts에 저장되어 final_answer_node에서 사용된다.

from __future__ import annotations

from typing import Any

from src.db_to_llm.shared.logging.logger import get_logger

logger = get_logger(__name__)

# Chroma 클라이언트 캐시 (반복 초기화 방지)
_chroma_collection_cache: dict[str, Any] = {}
_embedding_model_cache: dict[str, Any] = {}


def retrieve_contexts(
    query: str,
    config: dict[str, Any],
    top_k: int | None = None,
) -> list[dict[str, Any]]:
    """
    query와 유사한 문서 청크를 ChromaDB에서 검색해 반환한다.

    Args:
        query: 검색 쿼리. 사용자 질문 또는 "질문 + DB 요약" 형태.
        config: load_config()로 읽은 설정 dict.
        top_k: 반환할 최대 결과 수. None이면 config.retrieval.top_k를 사용한다.

    Returns:
        list[dict]: 검색된 청크 목록.
                    각 항목은 {document, metadata, distance, rank} 키를 포함한다.
    """
    retrieval_config = config.get("retrieval", {})
    chroma_path = str(retrieval_config.get("chroma_path", "data/chroma"))
    collection_name = str(retrieval_config.get("collection_name", "doc_chunks"))
    embedding_model_name = str(retrieval_config.get(
        "embedding_model",
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    ))
    actual_top_k = top_k or int(retrieval_config.get("top_k", 3))

    logger.info(
        "RAG 검색 시작: query_length=%d, top_k=%d, collection=%s",
        len(query),
        actual_top_k,
        collection_name,
    )

    # 쿼리 임베딩
    embedding_vector = _embed_query(query, embedding_model_name)

    # Chroma 검색
    collection = _get_collection(chroma_path, collection_name)

    try:
        results = collection.query(
            query_embeddings=[embedding_vector],
            n_results=actual_top_k,
            include=["documents", "metadatas", "distances"],
        )
    except Exception:
        logger.exception("ChromaDB 검색 실패: collection=%s", collection_name)
        raise

    # 결과 정리
    contexts: list[dict[str, Any]] = []
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    for rank, (doc, meta, dist) in enumerate(zip(documents, metadatas, distances), start=1):
        contexts.append({
            "rank": rank,
            "document": doc,
            "metadata": meta or {},
            "distance": float(dist),
        })
        logger.info(
            "검색 결과 [%d]: source=%s, distance=%.4f",
            rank,
            (meta or {}).get("file_name", "unknown"),
            float(dist),
        )

    logger.info("RAG 검색 완료: result_count=%d", len(contexts))
    return contexts


def build_context_block(contexts: list[dict[str, Any]]) -> str:
    """
    retrieved_contexts 목록을 프롬프트에 삽입할 텍스트 블록으로 변환한다.

    Args:
        contexts: retrieve_contexts()가 반환한 검색 결과 목록.

    Returns:
        str: "=== 검색 결과 1 ===\n텍스트\n..." 형식의 블록 문자열.
    """
    if not contexts:
        return "(검색된 문서가 없습니다)"

    blocks = []
    for ctx in contexts:
        rank = ctx.get("rank", "?")
        file_name = ctx.get("metadata", {}).get("file_name", "unknown")
        document = ctx.get("document", "")
        blocks.append(f"=== 검색 결과 {rank} (출처: {file_name}) ===\n{document}")

    return "\n\n".join(blocks)


def _embed_query(query: str, model_name: str) -> list[float]:
    """쿼리를 임베딩 벡터로 변환한다."""
    if model_name not in _embedding_model_cache:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as error:
            raise ImportError(
                "sentence-transformers 패키지가 없습니다. "
                "`pip install sentence-transformers`로 설치하세요."
            ) from error

        logger.info("임베딩 모델 로드: %s", model_name)
        _embedding_model_cache[model_name] = SentenceTransformer(model_name)

    model = _embedding_model_cache[model_name]
    vector = model.encode(query, normalize_embeddings=True)
    return vector.tolist()


def _get_collection(chroma_path: str, collection_name: str) -> Any:
    """Chroma 컬렉션을 가져온다. 이미 열려 있으면 캐시를 반환한다."""
    cache_key = f"{chroma_path}::{collection_name}"
    if cache_key in _chroma_collection_cache:
        return _chroma_collection_cache[cache_key]

    try:
        import chromadb
    except ImportError as error:
        raise ImportError(
            "chromadb 패키지가 없습니다. `pip install chromadb`로 설치하세요."
        ) from error

    client = chromadb.PersistentClient(path=chroma_path)
    collection = client.get_or_create_collection(name=collection_name)
    _chroma_collection_cache[cache_key] = collection
    return collection
