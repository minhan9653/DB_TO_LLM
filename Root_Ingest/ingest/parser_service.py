# This module orchestrates document parsing for the ingest pipeline.
# Parser implementation selection is delegated to parser factory/registry.
# Parsed outputs are normalized and saved as JSONL for downstream stages.
# Chunking/embedding/vector store layers are intentionally untouched.

from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from Root_Ingest.ingest.models import DocumentItem, ParsedDocument
from Root_Ingest.ingest.parsers.factory import create_parser, get_available_parsers
from Root_Ingest.utils.logger import get_logger
from Root_Ingest.utils.path_utils import ensure_directory

logger = get_logger(__name__)


def parse_documents(
    documents: list[DocumentItem],
    output_path: Path,
    parser_name: str,
    parser_options: dict[str, Any] | None = None,
) -> list[ParsedDocument]:
    """
    역할:
    INGEST 파싱 처리 입력 데이터를 파싱해 구조화된 형태로 변환합니다.
    
    Args:
    documents (list[DocumentItem]):
    역할: `parse_documents` 실행에 필요한 입력값입니다.
    값: 타입 힌트 기준 `list[DocumentItem]` 값이 전달됩니다.
    전달 출처: `INGEST 파싱 처리` 상위 호출부에서 전달됩니다.
    주의사항: 형식/범위가 함수 가정과 다르면 런타임 예외가 발생할 수 있습니다.
    output_path (Path):
    역할: JSONL/로그 등 결과 저장 경로입니다.
    값: `Path`입니다.
    전달 출처: config 경로를 `resolve_path()`한 값이 전달됩니다.
    주의사항: 부모 폴더가 없으면 먼저 `ensure_directory()`가 필요합니다.
    parser_name (str):
    역할: 리소스/모델/프롬프트의 이름 식별자입니다.
    값: 타입 힌트 기준 `str` 값이 전달됩니다.
    전달 출처: `INGEST 파싱 처리` 상위 호출부에서 전달됩니다.
    주의사항: 형식/범위가 함수 가정과 다르면 런타임 예외가 발생할 수 있습니다.
    parser_options (dict[str, Any] | None):
    역할: `parse_documents` 실행에 필요한 입력값입니다.
    값: 타입 힌트 기준 `dict[str, Any] | None` 값이 전달됩니다.
    전달 출처: `INGEST 파싱 처리` 상위 호출부에서 전달됩니다.
    주의사항: 형식/범위가 함수 가정과 다르면 런타임 예외가 발생할 수 있습니다.
    
    Returns:
    list[ParsedDocument]: INGEST 파싱 처리 결과를 순회 가능한 목록으로 반환합니다.
    
    Raises:
    Exception: 내부 검증 실패 또는 하위 호출 오류 상황에서 발생할 수 있습니다.
    """
    try:
        parser = create_parser(parser_name=parser_name, options=parser_options)
    except (ValueError, ImportError) as error:
        logger.error(str(error))
        raise

    available = ", ".join(get_available_parsers())
    logger.info("파싱 시작: parser=%s, available=%s, input_documents=%d", parser.parser_name, available, len(documents))

    parsed_documents: list[ParsedDocument] = []
    failed_count = 0
    for document in documents:
        logger.info("파일 파싱 시작: parser=%s, file=%s", parser.parser_name, document.file_name)
        try:
            parsed_doc = parser.parse(document)
            parsed_documents.append(parsed_doc)
            logger.info("파일 파싱 성공: parser=%s, file=%s", parser.parser_name, document.file_name)
        except ImportError:
            logger.error("파일 파싱 중 의존성 오류 발생: parser=%s, file=%s", parser.parser_name, document.file_name)
            raise
        except Exception:
            logger.exception("파일 파싱 실패: parser=%s, file=%s", parser.parser_name, document.file_name)
            failed_count += 1

    save_parsed_documents(parsed_documents, output_path)
    logger.info(
        "파싱 완료: parser=%s, success_documents=%d, failed_documents=%d",
        parser.parser_name,
        len(parsed_documents),
        failed_count,
    )
    return parsed_documents


def save_parsed_documents(parsed_documents: list[ParsedDocument], output_path: Path) -> None:
    """
    역할:
    INGEST 파싱 처리 결과를 파일로 직렬화해 다음 단계에서 재사용 가능하게 저장합니다.
    
    Args:
    parsed_documents (list[ParsedDocument]):
    역할: `save_parsed_documents` 실행에 필요한 입력값입니다.
    값: 타입 힌트 기준 `list[ParsedDocument]` 값이 전달됩니다.
    전달 출처: `INGEST 파싱 처리` 상위 호출부에서 전달됩니다.
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
    logger.info("파싱 결과 저장 시작: %s", output_path)
    ensure_directory(output_path.parent)
    with output_path.open("w", encoding="utf-8") as file:
        for parsed_document in parsed_documents:
            file.write(json.dumps(parsed_document.to_dict(), ensure_ascii=False) + "\n")
    logger.info("파싱 결과 저장 완료: total=%d", len(parsed_documents))


def load_parsed_documents(input_path: Path) -> list[ParsedDocument]:
    """
    역할:
    INGEST 파싱 처리에서 파일/설정을 읽어 메모리 객체로 변환합니다.
    
    Args:
    input_path (Path):
    역할: 로드할 입력 파일 경로입니다.
    값: `Path`입니다.
    전달 출처: 이전 단계 저장 파일 경로가 전달됩니다.
    주의사항: 파일 미존재/인코딩 오류 시 로딩 단계에서 예외가 납니다.
    
    Returns:
    list[ParsedDocument]: INGEST 파싱 처리 결과를 순회 가능한 목록으로 반환합니다.
    
    Raises:
    Exception: 명시적 raise가 없어도 파일 I/O, 네트워크, 외부 라이브러리 예외가 전파될 수 있습니다.
    """
    logger.info("파싱 결과 로드 시작: %s", input_path)
    if not input_path.exists():
        logger.warning("파싱 결과 파일이 없습니다: %s", input_path)
        return []

    parsed_documents: list[ParsedDocument] = []
    with input_path.open("r", encoding="utf-8") as file:
        for line in file:
            payload = json.loads(line)
            payload["metadata"] = _normalize_metadata(payload.get("metadata"))
            parsed_documents.append(ParsedDocument(**payload))
    logger.info("파싱 결과 로드 완료: total=%d", len(parsed_documents))
    return parsed_documents


def _normalize_metadata(metadata: Any) -> dict[str, Any]:
    """
    역할:
    INGEST 파싱 처리 입력값을 표준 형태로 정규화합니다.
    
    Args:
    metadata (Any):
    역할: `_normalize_metadata` 실행에 필요한 입력값입니다.
    값: 타입 힌트 기준 `Any` 값이 전달됩니다.
    전달 출처: `INGEST 파싱 처리` 상위 호출부에서 전달됩니다.
    주의사항: 형식/범위가 함수 가정과 다르면 런타임 예외가 발생할 수 있습니다.
    
    Returns:
    dict[str, Any]: INGEST 파싱 처리 단계에서 후속 처리에 바로 사용할 매핑 데이터를 반환합니다.
    
    Raises:
    Exception: 명시적 raise가 없어도 파일 I/O, 네트워크, 외부 라이브러리 예외가 전파될 수 있습니다.
    """
    if metadata is None:
        return {}
    if isinstance(metadata, dict):
        return metadata
    return {"_raw_metadata": str(metadata)}
