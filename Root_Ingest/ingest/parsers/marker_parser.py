# This module implements the marker-backed parser for ingest.

# It tries marker APIs for PDF parsing and keeps non-PDF handling stable.

# Results are normalized to plain text so downstream logic stays unchanged.

# Missing marker dependencies raise a clear installation guidance message.

from __future__ import annotations
import importlib
from pathlib import Path
from typing import Any, Callable
from Root_Ingest.ingest.models import DocumentItem
from Root_Ingest.ingest.parsers.base import BaseParser, TEXT_FILE_EXTENSIONS


class MarkerParser(BaseParser):
    """Parser implementation that prioritizes marker for PDF parsing."""

    parser_name = "marker"

    def __init__(self, options: dict[str, Any] | None = None) -> None:
        """
        역할:
        Marker 파서에 필요한 초기 속성과 의존성을 설정합니다.
        
        Args:
        options (dict[str, Any] | None):
        역할: `__init__` 실행에 필요한 입력값입니다.
        값: 타입 힌트 기준 `dict[str, Any] | None` 값이 전달됩니다.
        전달 출처: `Marker 파서` 상위 호출부에서 전달됩니다.
        주의사항: 형식/범위가 함수 가정과 다르면 런타임 예외가 발생할 수 있습니다.
        
        Returns:
        None: 반환값 없이 내부 상태 업데이트, 로깅, 파일 저장 같은 부수효과를 수행합니다.
        
        Raises:
        Exception: 명시적 raise가 없어도 파일 I/O, 네트워크, 외부 라이브러리 예외가 전파될 수 있습니다.
        """

        super().__init__(options=options)

        self._validate_marker_dependency()

        raw_convert_kwargs = self.options.get("convert_kwargs", {})

        self.convert_kwargs = raw_convert_kwargs if isinstance(raw_convert_kwargs, dict) else {}

        raw_converter_kwargs = self.options.get("converter_kwargs", {})

        self.converter_kwargs = raw_converter_kwargs if isinstance(raw_converter_kwargs, dict) else {}

    def extract_text(self, document: DocumentItem, source_path: Path) -> str:
        """
        역할:
        Marker 파서에서 필요한 핵심 텍스트/필드를 추출합니다.
        
        Args:
        document (DocumentItem):
        역할: `extract_text` 실행에 필요한 입력값입니다.
        값: 타입 힌트 기준 `DocumentItem` 값이 전달됩니다.
        전달 출처: `Marker 파서` 상위 호출부에서 전달됩니다.
        주의사항: 형식/범위가 함수 가정과 다르면 런타임 예외가 발생할 수 있습니다.
        source_path (Path):
        역할: 파일 또는 디렉터리 경로를 지정합니다.
        값: 타입 힌트 기준 `Path` 값이 전달됩니다.
        전달 출처: config 해석 결과 또는 이전 단계 계산 결과가 전달됩니다.
        주의사항: 상대 경로 기준이 다르면 의도하지 않은 위치를 참조할 수 있습니다.
        
        Returns:
        str: 텍스트/프롬프트/SQL 문자열 결과를 반환합니다.
        
        Raises:
        ValueError: 내부 검증 실패 또는 하위 호출 오류 상황에서 발생할 수 있습니다.
        """

        file_type = document.file_type.lower()
        if file_type in TEXT_FILE_EXTENSIONS:
            return self._parse_text_file(source_path)

        if file_type == ".docx":
            return self._parse_docx_with_python_docx(source_path)

        if file_type == ".pdf":
            return self._parse_pdf_with_marker(source_path)

        raise ValueError(f"지원하지 않는 파일 형식입니다: {file_type}")

    def _parse_pdf_with_marker(self, source_path: Path) -> str:
        """
        역할:
        Marker 파서 문맥에서 `_parse_pdf_with_marker` 기능을 수행합니다.
        
        Args:
        source_path (Path):
        역할: 파일 또는 디렉터리 경로를 지정합니다.
        값: 타입 힌트 기준 `Path` 값이 전달됩니다.
        전달 출처: config 해석 결과 또는 이전 단계 계산 결과가 전달됩니다.
        주의사항: 상대 경로 기준이 다르면 의도하지 않은 위치를 참조할 수 있습니다.
        
        Returns:
        str: 텍스트/프롬프트/SQL 문자열 결과를 반환합니다.
        
        Raises:
        RuntimeError: 내부 검증 실패 또는 하위 호출 오류 상황에서 발생할 수 있습니다.
        """

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
        """
        역할:
        Marker 파서 문맥에서 `_validate_marker_dependency` 기능을 수행합니다.
        
        Returns:
        None: 반환값 없이 내부 상태 업데이트, 로깅, 파일 저장 같은 부수효과를 수행합니다.
        
        Raises:
        ImportError: 내부 검증 실패 또는 하위 호출 오류 상황에서 발생할 수 있습니다.
        """
        try:
            importlib.import_module("marker")

        except Exception as error:
            raise ImportError("marker parser를 사용하려면 marker 관련 패키지를 설치하세요.") from error

    @staticmethod

    def _load_convert_single_pdf_function() -> Callable[..., Any] | None:
        """
        역할:
        Marker 파서 문맥에서 `_load_convert_single_pdf_function` 기능을 수행합니다.
        
        Returns:
        Callable[..., Any] | None: Marker 파서 계산 결과를 `Callable[..., Any] | None` 타입으로 반환합니다.
        
        Raises:
        Exception: 명시적 raise가 없어도 파일 I/O, 네트워크, 외부 라이브러리 예외가 전파될 수 있습니다.
        """
        try:
            module = importlib.import_module("marker.convert")

        except Exception:
            return None

        candidate = getattr(module, "convert_single_pdf", None)
        if callable(candidate):
            return candidate

        return None

    @staticmethod

    def _load_pdf_converter_class() -> type[Any] | None:
        """
        역할:
        Marker 파서 문맥에서 `_load_pdf_converter_class` 기능을 수행합니다.
        
        Returns:
        type[Any] | None: Marker 파서 계산 결과를 `type[Any] | None` 타입으로 반환합니다.
        
        Raises:
        Exception: 명시적 raise가 없어도 파일 I/O, 네트워크, 외부 라이브러리 예외가 전파될 수 있습니다.
        """
        try:
            module = importlib.import_module("marker.converters.pdf")

        except Exception:
            return None

        candidate = getattr(module, "PdfConverter", None)
        if isinstance(candidate, type):
            return candidate

        return None

    def _extract_with_convert_single_pdf(

        self,

        convert_single_pdf: Callable[..., Any],

        source_path: Path,

    ) -> str:
        """
        역할:
        Marker 파서 문맥에서 `_extract_with_convert_single_pdf` 기능을 수행합니다.
        
        Args:
        convert_single_pdf (Callable[..., Any]):
        역할: `_extract_with_convert_single_pdf` 실행에 필요한 입력값입니다.
        값: 타입 힌트 기준 `Callable[..., Any]` 값이 전달됩니다.
        전달 출처: `Marker 파서` 상위 호출부에서 전달됩니다.
        주의사항: 형식/범위가 함수 가정과 다르면 런타임 예외가 발생할 수 있습니다.
        source_path (Path):
        역할: 파일 또는 디렉터리 경로를 지정합니다.
        값: 타입 힌트 기준 `Path` 값이 전달됩니다.
        전달 출처: config 해석 결과 또는 이전 단계 계산 결과가 전달됩니다.
        주의사항: 상대 경로 기준이 다르면 의도하지 않은 위치를 참조할 수 있습니다.
        
        Returns:
        str: 텍스트/프롬프트/SQL 문자열 결과를 반환합니다.
        
        Raises:
        Exception: 명시적 raise가 없어도 파일 I/O, 네트워크, 외부 라이브러리 예외가 전파될 수 있습니다.
        """
        try:
            result = convert_single_pdf(str(source_path), **self.convert_kwargs)

        except TypeError:
            result = convert_single_pdf(str(source_path))

        return self._coerce_to_text(result)

    def _extract_with_pdf_converter_class(

        self,

        pdf_converter_class: type[Any],

        source_path: Path,

    ) -> str:
        """
        역할:
        Marker 파서 문맥에서 `_extract_with_pdf_converter_class` 기능을 수행합니다.
        
        Args:
        pdf_converter_class (type[Any]):
        역할: `_extract_with_pdf_converter_class` 실행에 필요한 입력값입니다.
        값: 타입 힌트 기준 `type[Any]` 값이 전달됩니다.
        전달 출처: `Marker 파서` 상위 호출부에서 전달됩니다.
        주의사항: 형식/범위가 함수 가정과 다르면 런타임 예외가 발생할 수 있습니다.
        source_path (Path):
        역할: 파일 또는 디렉터리 경로를 지정합니다.
        값: 타입 힌트 기준 `Path` 값이 전달됩니다.
        전달 출처: config 해석 결과 또는 이전 단계 계산 결과가 전달됩니다.
        주의사항: 상대 경로 기준이 다르면 의도하지 않은 위치를 참조할 수 있습니다.
        
        Returns:
        str: 텍스트/프롬프트/SQL 문자열 결과를 반환합니다.
        
        Raises:
        RuntimeError: 내부 검증 실패 또는 하위 호출 오류 상황에서 발생할 수 있습니다.
        """

        converter = pdf_converter_class(**self.converter_kwargs)
        if hasattr(converter, "convert") and callable(converter.convert):
            result = converter.convert(str(source_path))

        elif callable(converter):
            result = converter(str(source_path))

        else:
            raise RuntimeError("marker PdfConverter 객체를 호출할 수 없습니다.")

        return self._coerce_to_text(result)
