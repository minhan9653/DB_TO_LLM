# 이 파일은 청크 텍스트를 임베딩 벡터로 변환하는 단계입니다.

# 모델명은 설정값으로 받아 교체 가능하도록 단순하게 구성했습니다.

# 임베딩 결과는 JSONL로 저장해 벡터DB 저장 전 확인할 수 있습니다.

# 예외 발생 시 로그를 남기고 상위로 전달해 문제를 숨기지 않습니다.

from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from Root_Ingest.ingest.models import ChunkItem, EmbeddingItem
from Root_Ingest.utils.logger import get_logger
from Root_Ingest.utils.path_utils import ensure_directory

logger = get_logger(__name__)


def create_embeddings(

    chunks: list[ChunkItem],

    model_name: str,

    batch_size: int,

    normalize_embeddings: bool,

    device: str | None,

    output_path: Path,

) -> list[EmbeddingItem]:
    """
    역할:
    INGEST 임베딩 생성 단계의 신규 산출물을 생성합니다.
    
    Args:
    chunks (list[ChunkItem]):
    역할: `create_embeddings` 실행에 필요한 입력값입니다.
    값: 타입 힌트 기준 `list[ChunkItem]` 값이 전달됩니다.
    전달 출처: `INGEST 임베딩 생성` 상위 호출부에서 전달됩니다.
    주의사항: 형식/범위가 함수 가정과 다르면 런타임 예외가 발생할 수 있습니다.
    model_name (str):
    역할: 리소스/모델/프롬프트의 이름 식별자입니다.
    값: 타입 힌트 기준 `str` 값이 전달됩니다.
    전달 출처: `INGEST 임베딩 생성` 상위 호출부에서 전달됩니다.
    주의사항: 형식/범위가 함수 가정과 다르면 런타임 예외가 발생할 수 있습니다.
    batch_size (int):
    역할: `create_embeddings` 실행에 필요한 입력값입니다.
    값: 타입 힌트 기준 `int` 값이 전달됩니다.
    전달 출처: `INGEST 임베딩 생성` 상위 호출부에서 전달됩니다.
    주의사항: 형식/범위가 함수 가정과 다르면 런타임 예외가 발생할 수 있습니다.
    normalize_embeddings (bool):
    역할: `create_embeddings` 실행에 필요한 입력값입니다.
    값: 타입 힌트 기준 `bool` 값이 전달됩니다.
    전달 출처: `INGEST 임베딩 생성` 상위 호출부에서 전달됩니다.
    주의사항: 형식/범위가 함수 가정과 다르면 런타임 예외가 발생할 수 있습니다.
    device (str | None):
    역할: `create_embeddings` 실행에 필요한 입력값입니다.
    값: 타입 힌트 기준 `str | None` 값이 전달됩니다.
    전달 출처: `INGEST 임베딩 생성` 상위 호출부에서 전달됩니다.
    주의사항: 형식/범위가 함수 가정과 다르면 런타임 예외가 발생할 수 있습니다.
    output_path (Path):
    역할: JSONL/로그 등 결과 저장 경로입니다.
    값: `Path`입니다.
    전달 출처: config 경로를 `resolve_path()`한 값이 전달됩니다.
    주의사항: 부모 폴더가 없으면 먼저 `ensure_directory()`가 필요합니다.
    
    Returns:
    list[EmbeddingItem]: INGEST 임베딩 생성 결과를 순회 가능한 목록으로 반환합니다.
    
    Raises:
    Exception: 내부 검증 실패 또는 하위 호출 오류 상황에서 발생할 수 있습니다.
    ValueError: 내부 검증 실패 또는 하위 호출 오류 상황에서 발생할 수 있습니다.
    """

    logger.info("임베딩 시작: chunk_count=%d, model=%s", len(chunks), model_name)
    if batch_size <= 0:
        raise ValueError("batch_size must be greater than 0.")

    if not chunks:
        logger.warning("임베딩할 청크가 없습니다.")

        save_embeddings([], output_path)
        return []

    model = _load_sentence_transformer(model_name=model_name, device=device)

    chunk_texts = [chunk.chunk_text for chunk in chunks]
    try:
        vectors = model.encode(

            chunk_texts,

            batch_size=batch_size,

            show_progress_bar=False,

            normalize_embeddings=normalize_embeddings,

        )

    except Exception:
        logger.exception("임베딩 생성 실패")

        raise

    embedding_items: list[EmbeddingItem] = []
    for chunk, vector in zip(chunks, vectors, strict=True):
        embedding_items.append(

            EmbeddingItem(

                chunk_id=chunk.chunk_id,

                parent_document_id=chunk.parent_document_id,

                chunk_text=chunk.chunk_text,

                embedding=[float(value) for value in vector],

                metadata=_normalize_metadata(chunk.metadata),

            )

        )

    save_embeddings(embedding_items, output_path)

    logger.info("임베딩 완료: 총 %d건", len(embedding_items))
    return embedding_items


def save_embeddings(embeddings: list[EmbeddingItem], output_path: Path) -> None:
    """
    역할:
    INGEST 임베딩 생성 결과를 파일로 직렬화해 다음 단계에서 재사용 가능하게 저장합니다.
    
    Args:
    embeddings (list[EmbeddingItem]):
    역할: `save_embeddings` 실행에 필요한 입력값입니다.
    값: 타입 힌트 기준 `list[EmbeddingItem]` 값이 전달됩니다.
    전달 출처: `INGEST 임베딩 생성` 상위 호출부에서 전달됩니다.
    주의사항: 형식/범위가 함수 가정과 다르면 런타임 예외가 발생할 수 있습니다.
    output_path (Path):
    역할: JSONL/로그 등 결과 저장 경로입니다.
    값: `Path`입니다.
    전달 출처: config 경로를 `resolve_path()`한 값이 전달됩니다.
    주의사항: 부모 폴더가 없으면 먼저 `ensure_directory()`가 필요합니다.
    
    Returns:
    None: 반환값 없이 내부 상태 업데이트, 로깅, 파일 저장 같은 부수효과를 수행합니다.
    
    Raises:
    Exception: 명시적 raise가 없어도 파일 I/O, 네트워크, 외부 라이브러리 예외가 전파될 수 있습니다.
    """

    logger.info("임베딩 결과 저장 시작: %s", output_path)

    ensure_directory(output_path.parent)

    with output_path.open("w", encoding="utf-8") as file:
        for embedding in embeddings:
            file.write(json.dumps(embedding.to_dict(), ensure_ascii=False) + "\n")

    logger.info("임베딩 결과 저장 완료: 총 %d건", len(embeddings))


def load_embeddings(input_path: Path) -> list[EmbeddingItem]:
    """
    역할:
    INGEST 임베딩 생성에서 파일/설정을 읽어 메모리 객체로 변환합니다.
    
    Args:
    input_path (Path):
    역할: 로드할 입력 파일 경로입니다.
    값: `Path`입니다.
    전달 출처: 이전 단계 저장 파일 경로가 전달됩니다.
    주의사항: 파일 미존재/인코딩 오류 시 로딩 단계에서 예외가 납니다.
    
    Returns:
    list[EmbeddingItem]: INGEST 임베딩 생성 결과를 순회 가능한 목록으로 반환합니다.
    
    Raises:
    Exception: 명시적 raise가 없어도 파일 I/O, 네트워크, 외부 라이브러리 예외가 전파될 수 있습니다.
    """

    logger.info("임베딩 결과 로드 시작: %s", input_path)
    if not input_path.exists():
        logger.warning("임베딩 결과 파일이 없습니다: %s", input_path)
        return []

    embeddings: list[EmbeddingItem] = []

    with input_path.open("r", encoding="utf-8") as file:
        for line in file:
            payload = json.loads(line)

            payload["metadata"] = _normalize_metadata(payload.get("metadata"))

            embeddings.append(EmbeddingItem(**payload))

    logger.info("임베딩 결과 로드 완료: 총 %d건", len(embeddings))
    return embeddings


def _load_sentence_transformer(model_name: str, device: str | None) -> Any:
    """
    역할:
    INGEST 임베딩 생성 문맥에서 `_load_sentence_transformer` 기능을 수행합니다.
    
    Args:
    model_name (str):
    역할: 리소스/모델/프롬프트의 이름 식별자입니다.
    값: 타입 힌트 기준 `str` 값이 전달됩니다.
    전달 출처: `INGEST 임베딩 생성` 상위 호출부에서 전달됩니다.
    주의사항: 형식/범위가 함수 가정과 다르면 런타임 예외가 발생할 수 있습니다.
    device (str | None):
    역할: `_load_sentence_transformer` 실행에 필요한 입력값입니다.
    값: 타입 힌트 기준 `str | None` 값이 전달됩니다.
    전달 출처: `INGEST 임베딩 생성` 상위 호출부에서 전달됩니다.
    주의사항: 형식/범위가 함수 가정과 다르면 런타임 예외가 발생할 수 있습니다.
    
    Returns:
    Any: INGEST 임베딩 생성 계산 결과를 `Any` 타입으로 반환합니다.
    
    Raises:
    Exception: 내부 검증 실패 또는 하위 호출 오류 상황에서 발생할 수 있습니다.
    """

    logger.info("임베딩 모델 로딩 시작: %s", model_name)
    try:
        from sentence_transformers import SentenceTransformer

    except Exception:
        logger.exception("sentence-transformers import 실패")

        raise

    try:
        model = SentenceTransformer(model_name, device=device)

    except Exception:
        logger.exception("임베딩 모델 로딩 실패: %s", model_name)

        raise

    logger.info("임베딩 모델 로딩 완료: %s", model_name)
    return model


def _normalize_metadata(metadata: Any) -> dict[str, Any]:
    """
    역할:
    INGEST 임베딩 생성 입력값을 표준 형태로 정규화합니다.
    
    Args:
    metadata (Any):
    역할: `_normalize_metadata` 실행에 필요한 입력값입니다.
    값: 타입 힌트 기준 `Any` 값이 전달됩니다.
    전달 출처: `INGEST 임베딩 생성` 상위 호출부에서 전달됩니다.
    주의사항: 형식/범위가 함수 가정과 다르면 런타임 예외가 발생할 수 있습니다.
    
    Returns:
    dict[str, Any]: INGEST 임베딩 생성 단계에서 후속 처리에 바로 사용할 매핑 데이터를 반환합니다.
    
    Raises:
    Exception: 명시적 raise가 없어도 파일 I/O, 네트워크, 외부 라이브러리 예외가 전파될 수 있습니다.
    """
    if metadata is None:
        return {}

    if isinstance(metadata, dict):
        return metadata

    return {"_raw_metadata": str(metadata)}
