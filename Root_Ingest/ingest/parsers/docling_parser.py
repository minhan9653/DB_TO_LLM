# This module implements the docling-backed parser for ingest.

# It uses docling for rich documents and keeps text file parsing lightweight.

# All outputs are normalized into ParsedDocument through BaseParser.

# Import errors are converted to a user-friendly installation message.

from __future__ import annotations
from pathlib import Path
from typing import Any
from Root_Ingest.ingest.models import DocumentItem
from Root_Ingest.ingest.parsers.base import BaseParser, TEXT_FILE_EXTENSIONS


class DoclingParser(BaseParser):
    """Parser implementation that uses docling as first-choice backend."""

    parser_name = "docling"

    def __init__(self, options: dict[str, Any] | None = None) -> None:
        """
        역할:
        Docling 파서에 필요한 초기 속성과 의존성을 설정합니다.
        
        Args:
        options (dict[str, Any] | None):
        역할: `__init__` 실행에 필요한 입력값입니다.
        값: 타입 힌트 기준 `dict[str, Any] | None` 값이 전달됩니다.
        전달 출처: `Docling 파서` 상위 호출부에서 전달됩니다.
        주의사항: 형식/범위가 함수 가정과 다르면 런타임 예외가 발생할 수 있습니다.
        
        Returns:
        None: 반환값 없이 내부 상태 업데이트, 로깅, 파일 저장 같은 부수효과를 수행합니다.
        
        Raises:
        Exception: 명시적 raise가 없어도 파일 I/O, 네트워크, 외부 라이브러리 예외가 전파될 수 있습니다.
        """

        super().__init__(options=options)

        raw_converter_kwargs = self.options.get("converter_kwargs", {})

        self.converter_kwargs = raw_converter_kwargs if isinstance(raw_converter_kwargs, dict) else {}

        self._document_converter_class = self._load_document_converter_class()

        self._converter: Any | None = None

    def extract_text(self, document: DocumentItem, source_path: Path) -> str:
        """
        역할:
        Docling 파서에서 필요한 핵심 텍스트/필드를 추출합니다.
        
        Args:
        document (DocumentItem):
        역할: `extract_text` 실행에 필요한 입력값입니다.
        값: 타입 힌트 기준 `DocumentItem` 값이 전달됩니다.
        전달 출처: `Docling 파서` 상위 호출부에서 전달됩니다.
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

        file_type = document.file_type.lower()
        if file_type in TEXT_FILE_EXTENSIONS:
            return self._parse_text_file(source_path)

        return self._parse_with_docling(source_path)

    def _parse_with_docling(self, source_path: Path) -> str:
        """
        역할:
        Docling 파서 문맥에서 `_parse_with_docling` 기능을 수행합니다.
        
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

        converter = self._get_converter()

        result = converter.convert(str(source_path))

        text = self._extract_text_from_docling_result(result)
        if text.strip():
            return text

        raise RuntimeError(f"docling parser returned empty text: {source_path}")

    def _get_converter(self) -> Any:
        """
        역할:
        Docling 파서에서 재사용 리소스(로거/컬렉션/모델)를 조회 또는 생성합니다.
        
        Returns:
        Any: Docling 파서 계산 결과를 `Any` 타입으로 반환합니다.
        
        Raises:
        Exception: 명시적 raise가 없어도 파일 I/O, 네트워크, 외부 라이브러리 예외가 전파될 수 있습니다.
        """
        if self._converter is not None:
            return self._converter

        self._converter = self._document_converter_class(**self.converter_kwargs)
        return self._converter

    @staticmethod

    def _load_document_converter_class() -> Any:
        """
        역할:
        Docling 파서 문맥에서 `_load_document_converter_class` 기능을 수행합니다.
        
        Returns:
        Any: Docling 파서 계산 결과를 `Any` 타입으로 반환합니다.
        
        Raises:
        ImportError: 내부 검증 실패 또는 하위 호출 오류 상황에서 발생할 수 있습니다.
        """
        try:
            from docling.document_converter import DocumentConverter

        except Exception as error:
            raise ImportError("docling parser를 사용하려면 docling 패키지를 설치하세요.") from error

        return DocumentConverter

    def _extract_text_from_docling_result(self, result: Any) -> str:
        """
        역할:
        Docling 파서 문맥에서 `_extract_text_from_docling_result` 기능을 수행합니다.
        
        Args:
        result (Any):
        역할: `_extract_text_from_docling_result` 실행에 필요한 입력값입니다.
        값: 타입 힌트 기준 `Any` 값이 전달됩니다.
        전달 출처: `Docling 파서` 상위 호출부에서 전달됩니다.
        주의사항: 형식/범위가 함수 가정과 다르면 런타임 예외가 발생할 수 있습니다.
        
        Returns:
        str: 텍스트/프롬프트/SQL 문자열 결과를 반환합니다.
        
        Raises:
        Exception: 명시적 raise가 없어도 파일 I/O, 네트워크, 외부 라이브러리 예외가 전파될 수 있습니다.
        """

        document_object = getattr(result, "document", result)
        for method_name in ("export_to_markdown", "export_to_text", "to_markdown", "to_text"):
            method = getattr(document_object, method_name, None)
            if callable(method):
                method_output = method()

                text = self._coerce_to_text(method_output)
                if text.strip():
                    return text

        text = self._coerce_to_text(document_object)
        if text.strip():
            return text

        return self._coerce_to_text(result)
