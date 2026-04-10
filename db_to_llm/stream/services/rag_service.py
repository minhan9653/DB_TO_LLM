# 이 파일은 RAG 검색 로직을 노드에서 분리해 서비스 계층으로 제공한다.
# retrieval 설정 해석, 임베딩 생성, Chroma 조회를 한 곳에서 관리해 중복을 줄인다.
# 검색 결과는 dict 목록으로 표준화해 Graph state에 저장하기 쉽게 만든다.
# 예외는 로깅 후 재전파해 오케스트레이션 계층에서 오류 흐름을 제어할 수 있게 한다.

from __future__ import annotations

from pathlib import Path
from typing import Any

from Root_Stream.services.retrieval.chroma_retriever import ChromaRetriever
from Root_Stream.services.retrieval.embedding_service import SentenceTransformerEmbeddingService
from Root_Stream.utils.path_utils import resolve_path
from db_to_llm.common.logging.logger import get_logger

logger = get_logger(__name__)


def retrieve_contexts(
    *,
    config: dict[str, Any],
    project_root: Path,
    question: str,
) -> list[dict[str, Any]]:
    """
    질문을 임베딩해 Chroma에서 관련 컨텍스트를 조회한다.

    Args:
        config: stream 설정 dict.
        project_root: 프로젝트 루트 경로.
        question: 사용자 질문.

    Returns:
        list[dict[str, Any]]: 조회된 컨텍스트 목록.
    """
    retrieval_config = config.get("retrieval", {})
    if not bool(retrieval_config.get("enabled", False)):
        logger.info("RAG 조회 비활성화 상태라 빈 컨텍스트를 반환한다.")
        return []

    embedding_model = str(
        retrieval_config.get(
            "embedding_model",
            config.get("embedding", {}).get("model_name", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"),
        )
    )
    chroma_path = resolve_path(str(retrieval_config["chroma_path"]), project_root)
    collection_name = str(retrieval_config["collection_name"])
    top_k = int(retrieval_config.get("top_k", 3))

    logger.info("RAG 조회 시작: collection=%s, top_k=%d", collection_name, top_k)
    embedding_service = SentenceTransformerEmbeddingService(model_name=embedding_model)
    retriever = ChromaRetriever(
        persist_directory=chroma_path,
        collection_name=collection_name,
        top_k=top_k,
    )
    query_embedding = embedding_service.embed_query(question)
    contexts = retriever.retrieve(query_embedding)
    return [item.to_dict() for item in contexts]


def build_context_block(retrieved_contexts: list[dict[str, Any]]) -> str:
    """
    RAG 프롬프트에 넣기 위한 컨텍스트 텍스트 블록을 생성한다.

    Args:
        retrieved_contexts: 조회된 컨텍스트 목록.

    Returns:
        str: 프롬프트 삽입용 컨텍스트 문자열.
    """
    if not retrieved_contexts:
        return "검색된 컨텍스트가 없습니다."

    lines: list[str] = []
    for index, item in enumerate(retrieved_contexts, start=1):
        lines.append(f"[{index}] chunk_id={item.get('chunk_id')}, score={item.get('score')}")
        lines.append(str(item.get("text", "")))
        lines.append("")
    return "\n".join(lines).strip()

