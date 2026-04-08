# 이 파일은 임베딩 데이터를 ChromaDB에 저장하는 단계입니다.

# 컬렉션 이름, 저장 경로, 배치 크기는 설정 파일에서 받습니다.

# 저장 전 메타데이터 타입을 정리해 Chroma 입력 오류를 줄입니다.

# 저장 건수와 샘플 조회 결과를 로그로 확인할 수 있게 구성했습니다.

from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from Root_Ingest.ingest.models import EmbeddingItem
from Root_Ingest.utils.logger import get_logger
from Root_Ingest.utils.path_utils import ensure_directory

logger = get_logger(__name__)


def upsert_embeddings_to_chroma(

    embeddings: list[EmbeddingItem],

    persist_directory: Path,

    collection_name: str,

    batch_size: int,

) -> int:
    """
    역할:
    INGEST Chroma 적재 문맥에서 `upsert_embeddings_to_chroma` 기능을 수행합니다.
    
    Args:
    embeddings (list[EmbeddingItem]):
    역할: `upsert_embeddings_to_chroma` 실행에 필요한 입력값입니다.
    값: 타입 힌트 기준 `list[EmbeddingItem]` 값이 전달됩니다.
    전달 출처: `INGEST Chroma 적재` 상위 호출부에서 전달됩니다.
    주의사항: 형식/범위가 함수 가정과 다르면 런타임 예외가 발생할 수 있습니다.
    persist_directory (Path):
    역할: Chroma DB 영속 저장 폴더를 지정합니다.
    값: `Path` 객체입니다.
    전달 출처: config의 chroma 경로 설정에서 전달됩니다.
    주의사항: 환경별 디렉터리를 분리하지 않으면 데이터가 섞일 수 있습니다.
    collection_name (str):
    역할: Chroma 컬렉션 식별 이름입니다.
    값: 문자열입니다.
    전달 출처: config `collection_name`에서 전달됩니다.
    주의사항: 같은 이름을 재사용하면 이전 데이터와 혼합될 수 있습니다.
    batch_size (int):
    역할: `upsert_embeddings_to_chroma` 실행에 필요한 입력값입니다.
    값: 타입 힌트 기준 `int` 값이 전달됩니다.
    전달 출처: `INGEST Chroma 적재` 상위 호출부에서 전달됩니다.
    주의사항: 형식/범위가 함수 가정과 다르면 런타임 예외가 발생할 수 있습니다.
    
    Returns:
    int: INGEST Chroma 적재 계산 결과를 `int` 타입으로 반환합니다.
    
    Raises:
    ValueError: 내부 검증 실패 또는 하위 호출 오류 상황에서 발생할 수 있습니다.
    """
    if batch_size <= 0:
        raise ValueError("batch_size must be greater than 0.")

    logger.info(

        "벡터 저장 시작: embedding_count=%d, collection=%s",

        len(embeddings),

        collection_name,

    )
    if not embeddings:
        logger.warning("저장할 임베딩이 없습니다.")
        return 0

    ensure_directory(persist_directory)

    _client, collection = _get_chroma_collection(persist_directory, collection_name)
    for start_index in range(0, len(embeddings), batch_size):
        batch = embeddings[start_index : start_index + batch_size]

        ids = [item.chunk_id for item in batch]

        documents = [item.chunk_text for item in batch]

        vectors = [item.embedding for item in batch]

        metadatas = [_sanitize_metadata(item.metadata) for item in batch]

        logger.info("벡터 배치 저장: start=%d, size=%d", start_index, len(batch))

        collection.upsert(ids=ids, documents=documents, embeddings=vectors, metadatas=metadatas)  # type: ignore[arg-type]

    stored_count = collection.count()

    logger.info("벡터 저장 완료: 컬렉션 총 건수=%d", stored_count)
    return stored_count


def sample_from_collection(

    persist_directory: Path,

    collection_name: str,

    limit: int = 5,

) -> Any:
    """
    역할:
    INGEST Chroma 적재 문맥에서 `sample_from_collection` 기능을 수행합니다.
    
    Args:
    persist_directory (Path):
    역할: Chroma DB 영속 저장 폴더를 지정합니다.
    값: `Path` 객체입니다.
    전달 출처: config의 chroma 경로 설정에서 전달됩니다.
    주의사항: 환경별 디렉터리를 분리하지 않으면 데이터가 섞일 수 있습니다.
    collection_name (str):
    역할: Chroma 컬렉션 식별 이름입니다.
    값: 문자열입니다.
    전달 출처: config `collection_name`에서 전달됩니다.
    주의사항: 같은 이름을 재사용하면 이전 데이터와 혼합될 수 있습니다.
    limit (int):
    역할: `sample_from_collection` 실행에 필요한 입력값입니다.
    값: 타입 힌트 기준 `int` 값이 전달됩니다.
    전달 출처: `INGEST Chroma 적재` 상위 호출부에서 전달됩니다.
    주의사항: 형식/범위가 함수 가정과 다르면 런타임 예외가 발생할 수 있습니다.
    
    Returns:
    Any: INGEST Chroma 적재 계산 결과를 `Any` 타입으로 반환합니다.
    
    Raises:
    Exception: 명시적 raise가 없어도 파일 I/O, 네트워크, 외부 라이브러리 예외가 전파될 수 있습니다.
    """

    logger.info("벡터 샘플 조회 시작: collection=%s, limit=%d", collection_name, limit)

    _, collection = _get_chroma_collection(persist_directory, collection_name)

    result = collection.peek(limit=limit)

    logger.info("벡터 샘플 조회 완료")
    return result


def _get_chroma_collection(persist_directory: Path, collection_name: str):
    """
    역할:
    INGEST Chroma 적재에서 재사용 리소스(로거/컬렉션/모델)를 조회 또는 생성합니다.
    
    Args:
    persist_directory (Path):
    역할: Chroma DB 영속 저장 폴더를 지정합니다.
    값: `Path` 객체입니다.
    전달 출처: config의 chroma 경로 설정에서 전달됩니다.
    주의사항: 환경별 디렉터리를 분리하지 않으면 데이터가 섞일 수 있습니다.
    collection_name (str):
    역할: Chroma 컬렉션 식별 이름입니다.
    값: 문자열입니다.
    전달 출처: config `collection_name`에서 전달됩니다.
    주의사항: 같은 이름을 재사용하면 이전 데이터와 혼합될 수 있습니다.
    
    Returns:
    Any: INGEST Chroma 적재 계산 결과를 `Any` 타입으로 반환합니다.
    
    Raises:
    Exception: 내부 검증 실패 또는 하위 호출 오류 상황에서 발생할 수 있습니다.
    """
    try:
        import chromadb

    except Exception:
        logger.exception("chromadb import 실패")

        raise

    try:
        client = chromadb.PersistentClient(path=str(persist_directory))

        collection = client.get_or_create_collection(name=collection_name)

    except Exception:
        logger.exception("Chroma 컬렉션 생성/조회 실패: %s", collection_name)

        raise

    return client, collection


def _sanitize_metadata(metadata: Any) -> dict[str, Any]:
    """
    역할:
    INGEST Chroma 적재 문맥에서 `_sanitize_metadata` 기능을 수행합니다.
    
    Args:
    metadata (Any):
    역할: `_sanitize_metadata` 실행에 필요한 입력값입니다.
    값: 타입 힌트 기준 `Any` 값이 전달됩니다.
    전달 출처: `INGEST Chroma 적재` 상위 호출부에서 전달됩니다.
    주의사항: 형식/범위가 함수 가정과 다르면 런타임 예외가 발생할 수 있습니다.
    
    Returns:
    dict[str, Any]: INGEST Chroma 적재 단계에서 후속 처리에 바로 사용할 매핑 데이터를 반환합니다.
    
    Raises:
    Exception: 명시적 raise가 없어도 파일 I/O, 네트워크, 외부 라이브러리 예외가 전파될 수 있습니다.
    """
    if metadata is None:
        return {"_has_metadata": False}

    if not isinstance(metadata, dict):
        return {"_raw_metadata": str(metadata)}

    sanitized: dict[str, Any] = {}
    for key, value in metadata.items():
        safe_key = str(key)
        if value is None:
            continue

        if isinstance(value, (str, int, float, bool)):
            sanitized[safe_key] = value

        elif isinstance(value, (dict, list, tuple)):
            sanitized[safe_key] = json.dumps(value, ensure_ascii=False, default=str)

        else:
            sanitized[safe_key] = str(value)

    if not sanitized:
        sanitized["_has_metadata"] = False

    return sanitized
