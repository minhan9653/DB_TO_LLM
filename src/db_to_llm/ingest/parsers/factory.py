# 이 파일은 파서 이름을 받아 적절한 파서 구현체를 생성하는 팩토리 함수를 담는다.
# 새 파서를 추가할 때 이 파일만 수정하면 pipeline에서 자동으로 사용 가능하다.
# config.ingest.parser 값으로 파서를 선택하며, 기본값은 simple이다.
# 지원하지 않는 파서 이름은 명확한 오류 메시지와 함께 실패한다.

from __future__ import annotations

from typing import Any

from src.db_to_llm.ingest.parsers.base import BaseParser
from src.db_to_llm.ingest.parsers.simple_parser import SimpleTextParser
from src.db_to_llm.shared.logging.logger import get_logger

logger = get_logger(__name__)

# 지원하는 파서 이름과 클래스 매핑
AVAILABLE_PARSERS: dict[str, type[BaseParser]] = {
    "simple": SimpleTextParser,
}

# 외부 라이브러리가 필요한 파서는 import 시도 후 등록
try:
    from src.db_to_llm.ingest.parsers.docling_parser import DoclingParser
    AVAILABLE_PARSERS["docling"] = DoclingParser
except ImportError:
    pass  # docling이 없으면 이 파서는 사용 불가

try:
    from src.db_to_llm.ingest.parsers.unstructured_parser import UnstructuredParser
    AVAILABLE_PARSERS["unstructured"] = UnstructuredParser
except ImportError:
    pass

try:
    from src.db_to_llm.ingest.parsers.marker_parser import MarkerParser
    AVAILABLE_PARSERS["marker"] = MarkerParser
except ImportError:
    pass


def create_parser(parser_name: str, options: dict[str, Any] | None = None) -> BaseParser:
    """
    파서 이름으로 파서 인스턴스를 생성해 반환한다.

    Args:
        parser_name: 사용할 파서 이름. 예: "simple", "docling"
        options: 파서별 옵션 dict.

    Returns:
        BaseParser: 생성된 파서 인스턴스.

    Raises:
        ValueError: 지원하지 않는 파서 이름인 경우 발생한다.
    """
    normalized_name = parser_name.strip().lower()
    logger.info("파서 생성 시작: parser_name=%s", normalized_name)

    if normalized_name not in AVAILABLE_PARSERS:
        available = ", ".join(sorted(AVAILABLE_PARSERS.keys()))
        raise ValueError(
            f"지원하지 않는 파서입니다: '{normalized_name}'. "
            f"사용 가능한 파서: {available}"
        )

    parser_class = AVAILABLE_PARSERS[normalized_name]
    parser = parser_class(options=options)
    logger.info("파서 생성 완료: %s", parser.parser_name)
    return parser


def get_available_parsers() -> list[str]:
    """현재 사용 가능한 파서 이름 목록을 반환한다."""
    return sorted(AVAILABLE_PARSERS.keys())
