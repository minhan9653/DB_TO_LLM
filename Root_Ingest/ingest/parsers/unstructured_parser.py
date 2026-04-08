# This module implements the unstructured-backed parser for ingest.

# It uses unstructured partition for rich files and text decoding for plain text.

# Extracted elements are joined into a normalized text payload.

# Missing dependencies raise a clear message with the install requirement.

from __future__ import annotations
from pathlib import Path
from typing import Any
from Root_Ingest.ingest.models import DocumentItem
from Root_Ingest.ingest.parsers.base import BaseParser, TEXT_FILE_EXTENSIONS


class UnstructuredParser(BaseParser):
    """Parser implementation that uses unstructured partition APIs."""

    parser_name = "unstructured"

    def __init__(self, options: dict[str, Any] | None = None) -> None:
        """
        역할:
        Unstructured 파서에 필요한 초기 속성과 의존성을 설정합니다.
        
        Args:
        options (dict[str, Any] | None):
        역할: `__init__` 실행에 필요한 입력값입니다.
        값: 타입 힌트 기준 `dict[str, Any] | None` 값이 전달됩니다.
        전달 출처: `Unstructured 파서` 상위 호출부에서 전달됩니다.
        주의사항: 형식/범위가 함수 가정과 다르면 런타임 예외가 발생할 수 있습니다.
        
        Returns:
        None: 반환값 없이 내부 상태 업데이트, 로깅, 파일 저장 같은 부수효과를 수행합니다.
        
        Raises:
        Exception: 명시적 raise가 없어도 파일 I/O, 네트워크, 외부 라이브러리 예외가 전파될 수 있습니다.
        """

        super().__init__(options=options)

        raw_partition_kwargs = self.options.get("partition_kwargs", {})

        self.partition_kwargs = raw_partition_kwargs if isinstance(raw_partition_kwargs, dict) else {}

        self._partition_function = self._load_partition_function()

    def extract_text(self, document: DocumentItem, source_path: Path) -> str:
        """
        역할:
        Unstructured 파서에서 필요한 핵심 텍스트/필드를 추출합니다.
        
        Args:
        document (DocumentItem):
        역할: `extract_text` 실행에 필요한 입력값입니다.
        값: 타입 힌트 기준 `DocumentItem` 값이 전달됩니다.
        전달 출처: `Unstructured 파서` 상위 호출부에서 전달됩니다.
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

        return self._parse_with_unstructured(source_path)

    def _parse_with_unstructured(self, source_path: Path) -> str:
        """
        역할:
        Unstructured 파서 문맥에서 `_parse_with_unstructured` 기능을 수행합니다.
        
        Args:
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

    def _load_partition_function():
        """
        역할:
        Unstructured 파서 문맥에서 `_load_partition_function` 기능을 수행합니다.
        
        Returns:
        Any: Unstructured 파서 계산 결과를 `Any` 타입으로 반환합니다.
        
        Raises:
        ImportError: 내부 검증 실패 또는 하위 호출 오류 상황에서 발생할 수 있습니다.
        """
        try:
            from unstructured.partition.auto import partition

        except Exception as error:
            raise ImportError("unstructured parser를 사용하려면 unstructured 패키지를 설치하세요.") from error

        return partition

    def _build_partition_kwargs(self, source_path: Path) -> dict[str, Any]:
        """
        역할:
        Unstructured 파서 문맥에서 `_build_partition_kwargs` 기능을 수행합니다.
        
        Args:
        source_path (Path):
        역할: 파일 또는 디렉터리 경로를 지정합니다.
        값: 타입 힌트 기준 `Path` 값이 전달됩니다.
        전달 출처: config 해석 결과 또는 이전 단계 계산 결과가 전달됩니다.
        주의사항: 상대 경로 기준이 다르면 의도하지 않은 위치를 참조할 수 있습니다.
        
        Returns:
        dict[str, Any]: Unstructured 파서 단계에서 후속 처리에 바로 사용할 매핑 데이터를 반환합니다.
        
        Raises:
        Exception: 명시적 raise가 없어도 파일 I/O, 네트워크, 외부 라이브러리 예외가 전파될 수 있습니다.
        """

        partition_kwargs = {"filename": str(source_path), **self.partition_kwargs}

        language_value = self.options.get("language")
        if language_value and "languages" not in partition_kwargs:
            partition_kwargs["languages"] = [str(language_value)]

        return partition_kwargs
