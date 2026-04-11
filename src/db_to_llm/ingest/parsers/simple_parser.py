# 이 파일은 텍스트/마크다운/SQL 파일을 직접 읽어 파싱하는 단순 파서다.
# PDF나 DOCX 같은 외부 라이브러리가 필요 없는 파일은 이 파서로 처리한다.
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

        Args:
            document: 문서 메타데이터.
            source_path: 파일 경로.

        Returns:
            str: 파일 전체 텍스트.
        """
        logger.info("텍스트 파일 파싱 시작: %s", source_path.name)
        text = self.read_text_file(source_path)
        logger.info("텍스트 파일 파싱 완료: char_count=%d", len(text))
        return text
