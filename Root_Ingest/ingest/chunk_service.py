# 이 파일은 파싱된 문서를 단순 규칙으로 청킹하는 모듈입니다.

# 1차 버전에서는 문자 수 기반 청킹을 기본으로 사용합니다.

# 청크 구조는 chunk_id, parent_document_id, metadata를 유지합니다.

# 이후 구조 기반 청킹으로 확장할 수 있도록 함수 분리를 유지합니다.

from __future__ import annotations
import json
from pathlib import Path
from Root_Ingest.ingest.models import ChunkItem, ParsedDocument
from Root_Ingest.utils.logger import get_logger
from Root_Ingest.utils.path_utils import ensure_directory

logger = get_logger(__name__)


def chunk_documents(

    parsed_documents: list[ParsedDocument],

    chunk_size: int,

    chunk_overlap: int,

    output_path: Path,

) -> list[ChunkItem]:
    """
    역할:
    INGEST 청킹 처리 문맥에서 `chunk_documents` 기능을 수행합니다.
    
    Args:
    parsed_documents (list[ParsedDocument]):
    역할: `chunk_documents` 실행에 필요한 입력값입니다.
    값: 타입 힌트 기준 `list[ParsedDocument]` 값이 전달됩니다.
    전달 출처: `INGEST 청킹 처리` 상위 호출부에서 전달됩니다.
    주의사항: 형식/범위가 함수 가정과 다르면 런타임 예외가 발생할 수 있습니다.
    chunk_size (int):
    역할: `chunk_documents` 실행에 필요한 입력값입니다.
    값: 타입 힌트 기준 `int` 값이 전달됩니다.
    전달 출처: `INGEST 청킹 처리` 상위 호출부에서 전달됩니다.
    주의사항: 형식/범위가 함수 가정과 다르면 런타임 예외가 발생할 수 있습니다.
    chunk_overlap (int):
    역할: `chunk_documents` 실행에 필요한 입력값입니다.
    값: 타입 힌트 기준 `int` 값이 전달됩니다.
    전달 출처: `INGEST 청킹 처리` 상위 호출부에서 전달됩니다.
    주의사항: 형식/범위가 함수 가정과 다르면 런타임 예외가 발생할 수 있습니다.
    output_path (Path):
    역할: JSONL/로그 등 결과 저장 경로입니다.
    값: `Path`입니다.
    전달 출처: config 경로를 `resolve_path()`한 값이 전달됩니다.
    주의사항: 부모 폴더가 없으면 먼저 `ensure_directory()`가 필요합니다.
    
    Returns:
    list[ChunkItem]: INGEST 청킹 처리 결과를 순회 가능한 목록으로 반환합니다.
    
    Raises:
    ValueError: 내부 검증 실패 또는 하위 호출 오류 상황에서 발생할 수 있습니다.
    """

    logger.info(

        "청킹 시작: 입력 문서 수=%d, chunk_size=%d, chunk_overlap=%d",

        len(parsed_documents),

        chunk_size,

        chunk_overlap,

    )
    if chunk_size <= 0:
        raise ValueError("chunk_size는 1 이상이어야 합니다.")

    if chunk_overlap < 0:
        raise ValueError("chunk_overlap은 0 이상이어야 합니다.")

    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap은 chunk_size보다 작아야 합니다.")

    all_chunks: list[ChunkItem] = []
    for parsed_doc in parsed_documents:
        logger.info("문서 청킹 시작: document_id=%s", parsed_doc.document_id)

        chunks = split_text_by_char_count(parsed_doc.raw_text, chunk_size, chunk_overlap)
        for chunk_index, chunk_text in enumerate(chunks):
            chunk_id = f"{parsed_doc.document_id}_chunk_{chunk_index:04d}"

            all_chunks.append(

                ChunkItem(

                    chunk_id=chunk_id,

                    parent_document_id=parsed_doc.document_id,

                    chunk_text=chunk_text,

                    chunk_index=chunk_index,

                    metadata={

                        **parsed_doc.metadata,

                        "source_path": parsed_doc.source_path,

                        "file_type": parsed_doc.file_type,

                    },

                )

            )

        logger.info(

            "문서 청킹 완료: document_id=%s, chunk_count=%d",

            parsed_doc.document_id,

            len(chunks),

        )

    save_chunks(all_chunks, output_path)

    logger.info("청킹 완료: 총 청크 수=%d", len(all_chunks))
    return all_chunks


def split_text_by_char_count(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """
    역할:
    INGEST 청킹 처리 문맥에서 `split_text_by_char_count` 기능을 수행합니다.
    
    Args:
    text (str):
    역할: `split_text_by_char_count` 실행에 필요한 입력값입니다.
    값: 타입 힌트 기준 `str` 값이 전달됩니다.
    전달 출처: `INGEST 청킹 처리` 상위 호출부에서 전달됩니다.
    주의사항: 형식/범위가 함수 가정과 다르면 런타임 예외가 발생할 수 있습니다.
    chunk_size (int):
    역할: `split_text_by_char_count` 실행에 필요한 입력값입니다.
    값: 타입 힌트 기준 `int` 값이 전달됩니다.
    전달 출처: `INGEST 청킹 처리` 상위 호출부에서 전달됩니다.
    주의사항: 형식/범위가 함수 가정과 다르면 런타임 예외가 발생할 수 있습니다.
    chunk_overlap (int):
    역할: `split_text_by_char_count` 실행에 필요한 입력값입니다.
    값: 타입 힌트 기준 `int` 값이 전달됩니다.
    전달 출처: `INGEST 청킹 처리` 상위 호출부에서 전달됩니다.
    주의사항: 형식/범위가 함수 가정과 다르면 런타임 예외가 발생할 수 있습니다.
    
    Returns:
    list[str]: INGEST 청킹 처리 결과를 순회 가능한 목록으로 반환합니다.
    
    Raises:
    Exception: 명시적 raise가 없어도 파일 I/O, 네트워크, 외부 라이브러리 예외가 전파될 수 있습니다.
    """
    if not text:
        return []

    chunks: list[str] = []

    start_index = 0

    text_length = len(text)
    while start_index < text_length:
        end_index = min(start_index + chunk_size, text_length)

        chunk_text = text[start_index:end_index].strip()
        if chunk_text:
            chunks.append(chunk_text)

        if end_index >= text_length:
            break

        start_index = end_index - chunk_overlap

    return chunks


def save_chunks(chunks: list[ChunkItem], output_path: Path) -> None:
    """
    역할:
    INGEST 청킹 처리 결과를 파일로 직렬화해 다음 단계에서 재사용 가능하게 저장합니다.
    
    Args:
    chunks (list[ChunkItem]):
    역할: `save_chunks` 실행에 필요한 입력값입니다.
    값: 타입 힌트 기준 `list[ChunkItem]` 값이 전달됩니다.
    전달 출처: `INGEST 청킹 처리` 상위 호출부에서 전달됩니다.
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

    logger.info("청킹 결과 저장 시작: %s", output_path)

    ensure_directory(output_path.parent)

    with output_path.open("w", encoding="utf-8") as file:
        for chunk in chunks:
            file.write(json.dumps(chunk.to_dict(), ensure_ascii=False) + "\n")

    logger.info("청킹 결과 저장 완료: 총 %d건", len(chunks))


def load_chunks(input_path: Path) -> list[ChunkItem]:
    """
    역할:
    INGEST 청킹 처리에서 파일/설정을 읽어 메모리 객체로 변환합니다.
    
    Args:
    input_path (Path):
    역할: 로드할 입력 파일 경로입니다.
    값: `Path`입니다.
    전달 출처: 이전 단계 저장 파일 경로가 전달됩니다.
    주의사항: 파일 미존재/인코딩 오류 시 로딩 단계에서 예외가 납니다.
    
    Returns:
    list[ChunkItem]: INGEST 청킹 처리 결과를 순회 가능한 목록으로 반환합니다.
    
    Raises:
    Exception: 명시적 raise가 없어도 파일 I/O, 네트워크, 외부 라이브러리 예외가 전파될 수 있습니다.
    """

    logger.info("청킹 결과 로드 시작: %s", input_path)
    if not input_path.exists():
        logger.warning("청킹 결과 파일이 없습니다: %s", input_path)
        return []

    chunks: list[ChunkItem] = []

    with input_path.open("r", encoding="utf-8") as file:
        for line in file:
            payload = json.loads(line)

            chunks.append(ChunkItem(**payload))

    logger.info("청킹 결과 로드 완료: 총 %d건", len(chunks))
    return chunks
