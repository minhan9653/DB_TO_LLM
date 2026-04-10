# 이 파일은 프로젝트 전역에서 공통으로 사용할 logger 설정을 담당한다.
# 시간/레벨/파일명/함수명/라인번호/메시지 형식을 강제해 디버깅 일관성을 유지한다.
# CLI, API, Notebook, Graph 노드가 동일 포맷 로그를 남기도록 단일 진입점을 제공한다.
# 기존 Root_Stream/Root_Ingest 로깅 규칙과 호환되도록 간단한 함수 형태를 유지한다.

from __future__ import annotations

import logging
from pathlib import Path

LOGGER_NAME = "db_to_llm"
LOG_FORMAT = "[%(asctime)s] [%(levelname)s] [%(filename)s:%(funcName)s:%(lineno)d] %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logger(log_level: str = "INFO", log_file_path: Path | None = None) -> logging.Logger:
    """
    공통 logger를 초기화한다.

    Args:
        log_level: 로그 레벨 문자열.
        log_file_path: 파일 로그를 함께 기록할 경로.

    Returns:
        logging.Logger: 공통 루트 logger 객체.
    """
    logger = logging.getLogger(LOGGER_NAME)
    level_value = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(level_value)

    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
    if not logger.handlers:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

    if log_file_path is not None:
        resolved_path = log_file_path.resolve()
        has_same_file_handler = any(
            isinstance(handler, logging.FileHandler) and Path(handler.baseFilename).resolve() == resolved_path
            for handler in logger.handlers
        )
        if not has_same_file_handler:
            resolved_path.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(resolved_path, encoding="utf-8")
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

    logger.propagate = False
    return logger


def get_logger(name: str | None = None) -> logging.Logger:
    """
    공통 logger 또는 하위 logger를 반환한다.

    Args:
        name: 하위 logger 이름.

    Returns:
        logging.Logger: 요청된 logger 객체.
    """
    base_logger = logging.getLogger(LOGGER_NAME)
    if not base_logger.handlers:
        base_logger = setup_logger()

    if not name:
        return base_logger
    return base_logger.getChild(name)

