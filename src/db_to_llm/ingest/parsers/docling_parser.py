# docling 라이브러리를 사용하는 파서 구현체.
# 텍스트 파일은 직접 읽고, 나머지 파일은 docling DocumentConverter로 파싱한다.
# docling 미설치 시 ImportError를 명확한 안내 메시지와 함께 발생시킨다.

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.db_to_llm.ingest.models import DocumentItem
from src.db_to_llm.ingest.parsers.base import BaseParser, TEXT_FILE_EXTENSIONS


class DoclingParser(BaseParser):
    """docling DocumentConverter를 백엔드로 사용하는 파서."""

    parser_name = "docling"

    def __init__(self, options: dict[str, Any] | None = None) -> None:
        super().__init__(options=options)
        raw_converter_kwargs = self.options.get("converter_kwargs", {})
        self.converter_kwargs = raw_converter_kwargs if isinstance(raw_converter_kwargs, dict) else {}
        self._document_converter_class = self._load_document_converter_class()
        self._converter: Any | None = None

    def extract_text(self, document: DocumentItem, source_path: Path) -> str:
        file_type = document.file_type.lower()
        if file_type in TEXT_FILE_EXTENSIONS:
            return self._parse_text_file(source_path)
        return self._parse_with_docling(source_path)

    def _parse_with_docling(self, source_path: Path) -> str:
        converter = self._get_converter()
        result = converter.convert(str(source_path))
        text = self._extract_text_from_docling_result(result)
        if text.strip():
            return text
        raise RuntimeError(f"docling parser가 빈 텍스트를 반환했습니다: {source_path}")

    def _get_converter(self) -> Any:
        if self._converter is not None:
            return self._converter
        self._converter = self._document_converter_class(**self.converter_kwargs)
        return self._converter

    @staticmethod
    def _load_document_converter_class() -> Any:
        try:
            from docling.document_converter import DocumentConverter
        except Exception as error:
            raise ImportError("docling parser를 사용하려면 docling 패키지를 설치하세요.") from error
        return DocumentConverter

    def _extract_text_from_docling_result(self, result: Any) -> str:
        document_object = getattr(result, "document", result)
        for method_name in ("export_to_markdown", "export_to_text", "to_markdown", "to_text"):
            method = getattr(document_object, method_name, None)
            if callable(method):
                text = self._coerce_to_text(method())
                if text.strip():
                    return text
        text = self._coerce_to_text(document_object)
        if text.strip():
            return text
        return self._coerce_to_text(result)
