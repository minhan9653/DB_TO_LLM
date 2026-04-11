# 이 파일은 DocumentItem 목록을 받아 파서를 통해 텍스트를 추출하는 2단계 담당이다.
# 파서 종류는 config.ingest.parser로 결정하며, parsers/factory.py가 생성을 담당한다.
# 파싱에 실패한 파일은 건너뛰고 로그를 남겨 나머지 파일 처리를 계속한다.
# 결과는 ParsedDocument 리스트로 반환하며 JSONL로도 저장할 수 있다.

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.db_to_llm.ingest.models import DocumentItem, ParsedDocument
from src.db_to_llm.ingest.parsers.factory import create_parser
from src.db_to_llm.shared.logging.logger import get_logger

logger = get_logger(__name__)


def parse_documents(
    documents: list[DocumentItem],
    parser_name: str = "simple",
    parser_options: dict[str, Any] | None = None,
) -> list[ParsedDocument]:
    """
    DocumentItem 목록을 파서로 처리해 ParsedDocument 목록을 반환한다.

    Args:
        documents: 1단계(collect_documents)에서 수집한 문서 목록.
        parser_name: 사용할 파서 이름. config.ingest.parser 값을 전달한다.
        parser_options: 파서별 추가 옵션.

    Returns:
        list[ParsedDocument]: 텍스트가 추출된 파싱 결과 목록.
    """
    logger.info("문서 파싱 시작: total=%d, parser=%s", len(documents), parser_name)

    parser = create_parser(parser_name, options=parser_options)
    parsed_documents: list[ParsedDocument] = []

    for document in documents:
        try:
            logger.info("파싱 시작: %s", document.file_name)
            parsed = parser.parse(document)
            parsed_documents.append(parsed)
            logger.info("파싱 완료: %s, char_count=%d", document.file_name, len(parsed.raw_text))
        except Exception as error:
            # 한 파일 실패 시 나머지 계속 처리
            logger.error("파싱 실패: %s, error=%s", document.file_name, error)

    logger.info("문서 파싱 완료: success=%d / total=%d", len(parsed_documents), len(documents))
    return parsed_documents


def save_parsed_documents(parsed_documents: list[ParsedDocument], output_path: Path) -> None:
    """
    ParsedDocument 목록을 JSONL 형식으로 저장한다.

    Args:
        parsed_documents: 저장할 파싱 결과 목록.
        output_path: 저장할 JSONL 파일 경로.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        for parsed in parsed_documents:
            file.write(json.dumps(parsed.to_dict(), ensure_ascii=False) + "\n")
    logger.info("파싱 결과 저장 완료: path=%s, count=%d", output_path, len(parsed_documents))
