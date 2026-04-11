# marker 라이브러리를 사용하는 파서 구현체.
# PDF는 marker API로 파싱하고, DOCX는 python-docx로, 텍스트 파일은 직접 읽는다.
# marker 미설치 시 ImportError를 명확한 안내 메시지와 함께 발생시킨다.

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any, Callable

from src.db_to_llm.ingest.models import DocumentItem
from src.db_to_llm.ingest.parsers.base import BaseParser, TEXT_FILE_EXTENSIONS


class MarkerParser(BaseParser):
    """marker를 PDF 파싱 백엔드로 사용하는 파서."""

    parser_name = "marker"

    def __init__(self, options: dict[str, Any] | None = None) -> None:
        super().__init__(options=options)
        self._validate_marker_dependency()
        raw_convert_kwargs = self.options.get("convert_kwargs", {})
        self.convert_kwargs = raw_convert_kwargs if isinstance(raw_convert_kwargs, dict) else {}
        raw_converter_kwargs = self.options.get("converter_kwargs", {})
        self.converter_kwargs = raw_converter_kwargs if isinstance(raw_converter_kwargs, dict) else {}

    def extract_text(self, document: DocumentItem, source_path: Path) -> str:
        file_type = document.file_type.lower()
        if file_type in TEXT_FILE_EXTENSIONS:
            return self._parse_text_file(source_path)
        if file_type == ".docx":
            return self._parse_docx_with_python_docx(source_path)
        if file_type == ".pdf":
            return self._parse_pdf_with_marker(source_path)
        raise ValueError(f"지원하지 않는 파일 형식입니다: {file_type}")

    def _parse_pdf_with_marker(self, source_path: Path) -> str:
        self._validate_marker_dependency()
        convert_single_pdf = self._load_convert_single_pdf_function()
        if convert_single_pdf is not None:
            text = self._extract_with_convert_single_pdf(convert_single_pdf, source_path)
            if text.strip():
                return text
        pdf_converter_class = self._load_pdf_converter_class()
        if pdf_converter_class is not None:
            text = self._extract_with_pdf_converter_class(pdf_converter_class, source_path)
            if text.strip():
                return text
        raise RuntimeError(
            "marker parser에서 사용 가능한 PDF 변환 API를 찾지 못했습니다. "
            "marker 패키지 버전과 설치 구성을 확인하세요."
        )

    @staticmethod
    def _validate_marker_dependency() -> None:
        try:
            importlib.import_module("marker")
        except Exception as error:
            raise ImportError("marker parser를 사용하려면 marker 관련 패키지를 설치하세요.") from error

    @staticmethod
    def _load_convert_single_pdf_function() -> Callable[..., Any] | None:
        try:
            module = importlib.import_module("marker.convert")
        except Exception:
            return None
        candidate = getattr(module, "convert_single_pdf", None)
        return candidate if callable(candidate) else None

    @staticmethod
    def _load_pdf_converter_class() -> type[Any] | None:
        try:
            module = importlib.import_module("marker.converters.pdf")
        except Exception:
            return None
        candidate = getattr(module, "PdfConverter", None)
        return candidate if isinstance(candidate, type) else None

    def _extract_with_convert_single_pdf(
        self, convert_single_pdf: Callable[..., Any], source_path: Path
    ) -> str:
        try:
            result = convert_single_pdf(str(source_path), **self.convert_kwargs)
        except TypeError:
            result = convert_single_pdf(str(source_path))
        return self._coerce_to_text(result)

    def _extract_with_pdf_converter_class(
        self, pdf_converter_class: type[Any], source_path: Path
    ) -> str:
        converter = pdf_converter_class(**self.converter_kwargs)
        if hasattr(converter, "convert") and callable(converter.convert):
            result = converter.convert(str(source_path))
        elif callable(converter):
            result = converter(str(source_path))
        else:
            raise RuntimeError("marker PdfConverter 객체를 호출할 수 없습니다.")
        return self._coerce_to_text(result)
