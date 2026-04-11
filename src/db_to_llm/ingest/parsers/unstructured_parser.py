# unstructured 라이브러리를 사용하는 파서 구현체.
# 텍스트 파일은 직접 읽고, 나머지는 unstructured partition API로 파싱한다.
# unstructured 미설치 시 ImportError를 명확한 안내 메시지와 함께 발생시킨다.

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.db_to_llm.ingest.models import DocumentItem
from src.db_to_llm.ingest.parsers.base import BaseParser, TEXT_FILE_EXTENSIONS


class UnstructuredParser(BaseParser):
    """unstructured partition API를 백엔드로 사용하는 파서."""

    parser_name = "unstructured"

    def __init__(self, options: dict[str, Any] | None = None) -> None:
        super().__init__(options=options)
        raw_partition_kwargs = self.options.get("partition_kwargs", {})
        self.partition_kwargs = raw_partition_kwargs if isinstance(raw_partition_kwargs, dict) else {}
        self._partition_function = self._load_partition_function()

    def extract_text(self, document: DocumentItem, source_path: Path) -> str:
        file_type = document.file_type.lower()
        if file_type in TEXT_FILE_EXTENSIONS:
            return self._parse_text_file(source_path)
        return self._parse_with_unstructured(source_path)

    def _parse_with_unstructured(self, source_path: Path) -> str:
        partition_kwargs = self._build_partition_kwargs(source_path)
        elements = self._partition_function(**partition_kwargs)
        text_parts: list[str] = []
        for element in elements:
            text_value = getattr(element, "text", None)
            if isinstance(text_value, str) and text_value.strip():
                text_parts.append(text_value.strip())
        if text_parts:
            return "\n".join(text_parts)
        return self._coerce_to_text(elements)

    @staticmethod
    def _load_partition_function() -> Any:
        try:
            from unstructured.partition.auto import partition
        except Exception as error:
            raise ImportError("unstructured parser를 사용하려면 unstructured 패키지를 설치하세요.") from error
        return partition

    def _build_partition_kwargs(self, source_path: Path) -> dict[str, Any]:
        partition_kwargs = {"filename": str(source_path), **self.partition_kwargs}
        language_value = self.options.get("language")
        if language_value and "languages" not in partition_kwargs:
            partition_kwargs["languages"] = [str(language_value)]
        return partition_kwargs
