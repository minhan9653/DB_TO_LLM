# 이 파일은 텍스트/마크다운/SQL 파일을 직접 읽어 파싱하는 단순 파서다.
# DOCX는 python-docx, PDF는 pypdf로 처리하며, 나머지는 텍스트로 직접 읽는다.
# BaseParser의 extract_text()를 구현해 청킹/임베딩 단계에 텍스트를 전달한다.
# 인코딩 문제는 BaseParser.read_text_file()이 자동으로 처리한다.

from __future__ import annotations

from pathlib import Path

from src.db_to_llm.ingest.models import DocumentItem
from src.db_to_llm.ingest.parsers.base import BaseParser
from src.db_to_llm.shared.logging.logger import get_logger

logger = get_logger(__name__)


class SimpleTextParser(BaseParser):
    """텍스트/SQL/마크다운 파일을 직접 읽는 단순 파서."""

    parser_name = "simple"

    def extract_text(self, document: DocumentItem, source_path: Path) -> str:
        """
        파일을 직접 읽어 텍스트를 반환한다.
        DOCX는 python-docx, PDF는 pypdf, 나머지는 텍스트로 처리한다.

        Args:
            document: 문서 메타데이터.
            source_path: 파일 경로.

        Returns:
            str: 파일 전체 텍스트.
        """
        suffix = source_path.suffix.lower()
        logger.info("파일 파싱 시작: %s", source_path.name)
        if suffix == ".docx":
            text = self._parse_docx_with_python_docx(source_path)
        elif suffix == ".pdf":
            text = self._parse_pdf_with_pypdf(source_path)
        else:
            text = self.read_text_file(source_path)
        logger.info("파일 파싱 완료: char_count=%d", len(text))
        return text
