# 이 파일은 doc 폴더에서 문서를 수집하는 1단계 로직입니다.

# 지원 확장자 필터링과 기본 메타데이터 생성 역할을 담당합니다.

# 결과는 JSONL로 저장해 Notebook에서 쉽게 재사용할 수 있습니다.

# 파일별 처리 시작/완료 로그를 남겨 추적 가능하게 구성했습니다.

from __future__ import annotations
import hashlib
import json
from pathlib import Path
from Root_Ingest.ingest.models import DocumentItem
from Root_Ingest.utils.logger import get_logger
from Root_Ingest.utils.path_utils import ensure_directory

logger = get_logger(__name__)


def collect_documents(doc_dir: Path, supported_extensions: list[str]) -> list[DocumentItem]:
    """
    역할:
    INGEST 문서 수집/저장 문맥에서 `collect_documents` 기능을 수행합니다.
    
    Args:
    doc_dir (Path):
    역할: `collect_documents` 실행에 필요한 입력값입니다.
    값: 타입 힌트 기준 `Path` 값이 전달됩니다.
    전달 출처: `INGEST 문서 수집/저장` 상위 호출부에서 전달됩니다.
    주의사항: 형식/범위가 함수 가정과 다르면 런타임 예외가 발생할 수 있습니다.
    supported_extensions (list[str]):
    역할: `collect_documents` 실행에 필요한 입력값입니다.
    값: 타입 힌트 기준 `list[str]` 값이 전달됩니다.
    전달 출처: `INGEST 문서 수집/저장` 상위 호출부에서 전달됩니다.
    주의사항: 형식/범위가 함수 가정과 다르면 런타임 예외가 발생할 수 있습니다.
    
    Returns:
    list[DocumentItem]: INGEST 문서 수집/저장 결과를 순회 가능한 목록으로 반환합니다.
    
    Raises:
    Exception: 명시적 raise가 없어도 파일 I/O, 네트워크, 외부 라이브러리 예외가 전파될 수 있습니다.
    """

    logger.info("문서 수집 시작: doc_dir=%s", doc_dir)
    if not doc_dir.exists():
        logger.warning("문서 폴더가 없습니다: %s", doc_dir)
        return []

    extensions = {ext.lower() for ext in supported_extensions}

    documents: list[DocumentItem] = []
    for file_path in sorted(doc_dir.rglob("*")):
        if not file_path.is_file():
            continue

        if file_path.suffix.lower() not in extensions:
            continue

        logger.info("파일 처리 시작: %s", file_path.name)

        stat_info = file_path.stat()

        document_id = _build_document_id(file_path, stat_info.st_size, int(stat_info.st_mtime))

        document = DocumentItem(

            document_id=document_id,

            source_path=str(file_path.resolve()),

            file_name=file_path.name,

            file_type=file_path.suffix.lower(),

            file_size=stat_info.st_size,

            metadata={

                "relative_path": str(file_path),

                "modified_time": int(stat_info.st_mtime),

            },

        )

        documents.append(document)

        logger.info("파일 처리 완료: %s", file_path.name)

    logger.info("문서 수집 완료: 총 %d건", len(documents))
    return documents


def save_documents_to_jsonl(documents: list[DocumentItem], output_path: Path) -> None:
    """
    역할:
    INGEST 문서 수집/저장 결과를 파일로 직렬화해 다음 단계에서 재사용 가능하게 저장합니다.
    
    Args:
    documents (list[DocumentItem]):
    역할: `save_documents_to_jsonl` 실행에 필요한 입력값입니다.
    값: 타입 힌트 기준 `list[DocumentItem]` 값이 전달됩니다.
    전달 출처: `INGEST 문서 수집/저장` 상위 호출부에서 전달됩니다.
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

    logger.info("문서 메타데이터 저장 시작: %s", output_path)

    ensure_directory(output_path.parent)

    with output_path.open("w", encoding="utf-8") as file:
        for document in documents:
            file.write(json.dumps(document.to_dict(), ensure_ascii=False) + "\n")

    logger.info("문서 메타데이터 저장 완료: 총 %d건", len(documents))


def load_documents_from_jsonl(input_path: Path) -> list[DocumentItem]:
    """
    역할:
    INGEST 문서 수집/저장에서 파일/설정을 읽어 메모리 객체로 변환합니다.
    
    Args:
    input_path (Path):
    역할: 로드할 입력 파일 경로입니다.
    값: `Path`입니다.
    전달 출처: 이전 단계 저장 파일 경로가 전달됩니다.
    주의사항: 파일 미존재/인코딩 오류 시 로딩 단계에서 예외가 납니다.
    
    Returns:
    list[DocumentItem]: INGEST 문서 수집/저장 결과를 순회 가능한 목록으로 반환합니다.
    
    Raises:
    Exception: 명시적 raise가 없어도 파일 I/O, 네트워크, 외부 라이브러리 예외가 전파될 수 있습니다.
    """

    logger.info("문서 메타데이터 로드 시작: %s", input_path)
    if not input_path.exists():
        logger.warning("문서 메타데이터 파일이 없습니다: %s", input_path)
        return []

    documents: list[DocumentItem] = []

    with input_path.open("r", encoding="utf-8") as file:
        for line in file:
            payload = json.loads(line)

            documents.append(DocumentItem(**payload))

    logger.info("문서 메타데이터 로드 완료: 총 %d건", len(documents))
    return documents


def _build_document_id(file_path: Path, file_size: int, modified_time: int) -> str:
    """
    역할:
    INGEST 문서 수집/저장 문맥에서 `_build_document_id` 기능을 수행합니다.
    
    Args:
    file_path (Path):
    역할: 파일 또는 디렉터리 경로를 지정합니다.
    값: 타입 힌트 기준 `Path` 값이 전달됩니다.
    전달 출처: config 해석 결과 또는 이전 단계 계산 결과가 전달됩니다.
    주의사항: 상대 경로 기준이 다르면 의도하지 않은 위치를 참조할 수 있습니다.
    file_size (int):
    역할: `_build_document_id` 실행에 필요한 입력값입니다.
    값: 타입 힌트 기준 `int` 값이 전달됩니다.
    전달 출처: `INGEST 문서 수집/저장` 상위 호출부에서 전달됩니다.
    주의사항: 형식/범위가 함수 가정과 다르면 런타임 예외가 발생할 수 있습니다.
    modified_time (int):
    역할: `_build_document_id` 실행에 필요한 입력값입니다.
    값: 타입 힌트 기준 `int` 값이 전달됩니다.
    전달 출처: `INGEST 문서 수집/저장` 상위 호출부에서 전달됩니다.
    주의사항: 형식/범위가 함수 가정과 다르면 런타임 예외가 발생할 수 있습니다.
    
    Returns:
    str: 텍스트/프롬프트/SQL 문자열 결과를 반환합니다.
    
    Raises:
    Exception: 명시적 raise가 없어도 파일 I/O, 네트워크, 외부 라이브러리 예외가 전파될 수 있습니다.
    """

    raw_key = f"{file_path.resolve()}|{file_size}|{modified_time}"
    return hashlib.sha1(raw_key.encode("utf-8")).hexdigest()[:16]
