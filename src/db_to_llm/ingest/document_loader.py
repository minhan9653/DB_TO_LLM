# 이 파일은 지정된 디렉터리에서 문서 파일을 수집하는 ingest 1단계 담당이다.
# 지원 확장자 필터링, 파일 메타데이터 수집, document_id 생성 역할을 수행한다.
# 결과는 DocumentItem 리스트로 반환하며 JSONL 파일로도 저장할 수 있다.
# 수집된 문서는 parser_service.py에 전달해 텍스트 추출 단계로 이어진다.

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from src.db_to_llm.ingest.models import DocumentItem
from src.db_to_llm.shared.logging.logger import get_logger

logger = get_logger(__name__)


def collect_documents(
    doc_dir: Path,
    supported_extensions: list[str],
) -> list[DocumentItem]:
    """
    doc_dir 하위에서 지원 확장자에 해당하는 파일을 모두 수집한다.

    Args:
        doc_dir: 문서가 있는 디렉터리 경로.
        supported_extensions: 처리할 확장자 목록. 예: [".pdf", ".txt", ".sql"]

    Returns:
        list[DocumentItem]: 수집된 문서 메타데이터 목록.
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

        logger.info("파일 발견: %s", file_path.name)

        stat_info = file_path.stat()
        document_id = _build_document_id(file_path, stat_info.st_size)

        document = DocumentItem(
            document_id=document_id,
            source_path=str(file_path.resolve()),
            file_name=file_path.name,
            file_type=file_path.suffix.lower(),
            file_size=stat_info.st_size,
            metadata={
                "relative_path": str(file_path),
                "last_modified": int(stat_info.st_mtime),
            },
        )
        documents.append(document)

    logger.info("문서 수집 완료: total=%d", len(documents))
    return documents


def save_documents_to_jsonl(documents: list[DocumentItem], output_path: Path) -> None:
    """
    DocumentItem 목록을 JSONL 형식으로 파일에 저장한다.

    Args:
        documents: 저장할 문서 목록.
        output_path: 저장할 JSONL 파일 경로.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        for document in documents:
            file.write(json.dumps(document.to_dict(), ensure_ascii=False) + "\n")
    logger.info("문서 목록 저장 완료: path=%s, count=%d", output_path, len(documents))


def _build_document_id(file_path: Path, file_size: int) -> str:
    """
    파일 경로와 크기를 조합해 MD5 기반 document_id를 생성한다.
    동일 파일이면 항상 같은 ID를 반환하므로 중복 ingest를 방지할 수 있다.
    """
    key = f"{file_path.resolve()}:{file_size}"
    return hashlib.md5(key.encode("utf-8")).hexdigest()
