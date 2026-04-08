# This module provides parser registry and factory helpers.

# Config values map to parser implementations through one central table.

# Ingest code only asks this factory for a parser instance.

# Invalid parser names are rejected with a clear, actionable message.

from __future__ import annotations
from typing import Any
from Root_Ingest.ingest.parsers.base import BaseParser
from Root_Ingest.ingest.parsers.docling_parser import DoclingParser
from Root_Ingest.ingest.parsers.marker_parser import MarkerParser
from Root_Ingest.ingest.parsers.unstructured_parser import UnstructuredParser

SUPPORTED_PARSERS = ("docling", "marker", "unstructured")

PARSER_REGISTRY: dict[str, type[BaseParser]] = {

    "docling": DoclingParser,

    "marker": MarkerParser,

    "unstructured": UnstructuredParser,

}


def get_available_parsers() -> tuple[str, ...]:
    """
    역할:
    파서 팩토리에서 재사용 리소스(로거/컬렉션/모델)를 조회 또는 생성합니다.
    
    Returns:
    tuple[str, ...]: 파서 팩토리 계산 결과를 `tuple[str, ...]` 타입으로 반환합니다.
    
    Raises:
    Exception: 명시적 raise가 없어도 파일 I/O, 네트워크, 외부 라이브러리 예외가 전파될 수 있습니다.
    """
    return SUPPORTED_PARSERS


def normalize_parser_name(parser_name: str) -> str:
    """
    역할:
    파서 팩토리 입력값을 표준 형태로 정규화합니다.
    
    Args:
    parser_name (str):
    역할: 리소스/모델/프롬프트의 이름 식별자입니다.
    값: 타입 힌트 기준 `str` 값이 전달됩니다.
    전달 출처: `파서 팩토리` 상위 호출부에서 전달됩니다.
    주의사항: 형식/범위가 함수 가정과 다르면 런타임 예외가 발생할 수 있습니다.
    
    Returns:
    str: 텍스트/프롬프트/SQL 문자열 결과를 반환합니다.
    
    Raises:
    Exception: 명시적 raise가 없어도 파일 I/O, 네트워크, 외부 라이브러리 예외가 전파될 수 있습니다.
    """
    return str(parser_name or "").strip().lower()


def validate_parser_name(parser_name: str) -> str:
    """
    역할:
    파서 팩토리 문맥에서 `validate_parser_name` 기능을 수행합니다.
    
    Args:
    parser_name (str):
    역할: 리소스/모델/프롬프트의 이름 식별자입니다.
    값: 타입 힌트 기준 `str` 값이 전달됩니다.
    전달 출처: `파서 팩토리` 상위 호출부에서 전달됩니다.
    주의사항: 형식/범위가 함수 가정과 다르면 런타임 예외가 발생할 수 있습니다.
    
    Returns:
    str: 텍스트/프롬프트/SQL 문자열 결과를 반환합니다.
    
    Raises:
    ValueError: 내부 검증 실패 또는 하위 호출 오류 상황에서 발생할 수 있습니다.
    """

    normalized_name = normalize_parser_name(parser_name)
    if normalized_name in PARSER_REGISTRY:
        return normalized_name

    available = ", ".join(get_available_parsers())

    raise ValueError(

        f"Unsupported parser: {parser_name}. Available parsers: {available}"

    )


def create_parser(parser_name: str, options: dict[str, Any] | None = None) -> BaseParser:
    """
    역할:
    파서 팩토리 단계의 신규 산출물을 생성합니다.
    
    Args:
    parser_name (str):
    역할: 리소스/모델/프롬프트의 이름 식별자입니다.
    값: 타입 힌트 기준 `str` 값이 전달됩니다.
    전달 출처: `파서 팩토리` 상위 호출부에서 전달됩니다.
    주의사항: 형식/범위가 함수 가정과 다르면 런타임 예외가 발생할 수 있습니다.
    options (dict[str, Any] | None):
    역할: `create_parser` 실행에 필요한 입력값입니다.
    값: 타입 힌트 기준 `dict[str, Any] | None` 값이 전달됩니다.
    전달 출처: `파서 팩토리` 상위 호출부에서 전달됩니다.
    주의사항: 형식/범위가 함수 가정과 다르면 런타임 예외가 발생할 수 있습니다.
    
    Returns:
    BaseParser: 파서 팩토리 계산 결과를 `BaseParser` 타입으로 반환합니다.
    
    Raises:
    Exception: 명시적 raise가 없어도 파일 I/O, 네트워크, 외부 라이브러리 예외가 전파될 수 있습니다.
    """

    normalized_name = validate_parser_name(parser_name)

    parser_class = PARSER_REGISTRY[normalized_name]
    return parser_class(options=options or {})
