# 이 파일은 프로젝트 전체에서 공통으로 사용하는 로거를 설정한다.
# Rule.md 규정에 따라 [시간] [레벨] [파일명:함수명:라인번호] 메시지 형식을 사용한다.
# 콘솔과 파일 출력을 동시에 지원하며, 모든 모듈은 get_logger()로 로거를 가져다 쓴다.
# 민감 정보(API Key, DB 비밀번호)는 절대 로그에 남기지 않는다.

from __future__ import annotations

import logging
from pathlib import Path

# Rule.md 3-2 규정: 시간, 레벨, 파일명, 함수명, 라인번호 포함
LOG_FORMAT = "[%(asctime)s] [%(levelname)s] [%(filename)s:%(funcName)s:%(lineno)d] %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 프로젝트 전체 로거 이름 (하위 모듈은 child logger로 자동 상속)
BASE_LOGGER_NAME = "db_to_llm"


def setup_logger(log_level: str = "INFO", log_file_path: Path | None = None) -> logging.Logger:
    """
    프로젝트 루트 로거를 초기화하고 반환한다.
    이미 handler가 설정되어 있으면 중복 추가하지 않는다.

    Args:
        log_level: 로그 레벨 문자열. "DEBUG", "INFO", "WARNING", "ERROR" 중 하나.
        log_file_path: 파일 로그 출력 경로. None이면 콘솔 로그만 출력한다.

    Returns:
        logging.Logger: 설정이 완료된 루트 로거 인스턴스.
    """
    logger = logging.getLogger(BASE_LOGGER_NAME)
    level_value = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(level_value)

    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    # 콘솔 핸들러가 없을 때만 추가 (중복 방지)
    if not logger.handlers:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # 파일 핸들러: 동일 경로가 이미 등록된 경우 스킵
    if log_file_path is not None:
        resolved_path = log_file_path.resolve()
        already_added = any(
            isinstance(handler, logging.FileHandler)
            and Path(handler.baseFilename).resolve() == resolved_path
            for handler in logger.handlers
        )
        if not already_added:
            resolved_path.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(resolved_path, encoding="utf-8")
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

    logger.propagate = False
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    모듈별 child logger를 반환한다.
    루트 로거(db_to_llm)가 아직 초기화되지 않았으면 INFO 레벨로 자동 초기화한다.

    Args:
        name: 보통 __name__을 전달한다. 로거 이름으로 파일 위치를 추적할 수 있다.

    Returns:
        logging.Logger: 해당 모듈 전용 child logger.
    """
    # 루트 로거가 초기화되어 있지 않으면 기본 설정으로 초기화
    root_logger = logging.getLogger(BASE_LOGGER_NAME)
    if not root_logger.handlers:
        setup_logger()

    return logging.getLogger(name)
