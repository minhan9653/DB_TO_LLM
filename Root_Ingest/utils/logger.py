# 이 파일은 프로젝트 공통 로그 설정을 담당합니다.

# 로그 포맷은 시간, 레벨, 파일명, 함수명, 라인번호를 포함합니다.

# 모든 모듈은 여기의 logger를 재사용해 같은 형식으로 기록합니다.

# 콘솔과 파일 로그를 동시에 지원하도록 단순하게 구성했습니다.

from __future__ import annotations
import logging
from pathlib import Path

LOG_FORMAT = "[%(asctime)s] [%(levelname)s] [%(filename)s:%(funcName)s:%(lineno)d] %(message)s"

DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logger(log_level: str = "INFO", log_file_path: Path | None = None) -> logging.Logger:
    """
    역할:
    INGEST 로깅 설정 문맥에서 `setup_logger` 기능을 수행합니다.
    
    Args:
    log_level (str):
    역할: `setup_logger` 실행에 필요한 입력값입니다.
    값: 타입 힌트 기준 `str` 값이 전달됩니다.
    전달 출처: `INGEST 로깅 설정` 상위 호출부에서 전달됩니다.
    주의사항: 형식/범위가 함수 가정과 다르면 런타임 예외가 발생할 수 있습니다.
    log_file_path (Path | None):
    역할: 파일 또는 디렉터리 경로를 지정합니다.
    값: 타입 힌트 기준 `Path | None` 값이 전달됩니다.
    전달 출처: config 해석 결과 또는 이전 단계 계산 결과가 전달됩니다.
    주의사항: 상대 경로 기준이 다르면 의도하지 않은 위치를 참조할 수 있습니다.
    
    Returns:
    logging.Logger: INGEST 로깅 설정 계산 결과를 `logging.Logger` 타입으로 반환합니다.
    
    Raises:
    Exception: 명시적 raise가 없어도 파일 I/O, 네트워크, 외부 라이브러리 예외가 전파될 수 있습니다.
    """

    logger = logging.getLogger("db_to_llm")

    level_value = getattr(logging, log_level.upper(), logging.INFO)

    logger.setLevel(level_value)

    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
    if not logger.handlers:
        stream_handler = logging.StreamHandler()

        stream_handler.setFormatter(formatter)

        logger.addHandler(stream_handler)

    if log_file_path is not None:
        resolved_log_path = log_file_path.resolve()

        has_same_file_handler = any(

            isinstance(handler, logging.FileHandler)

            and Path(handler.baseFilename).resolve() == resolved_log_path
            for handler in logger.handlers

        )
        if not has_same_file_handler:
            resolved_log_path.parent.mkdir(parents=True, exist_ok=True)

            file_handler = logging.FileHandler(resolved_log_path, encoding="utf-8")

            file_handler.setFormatter(formatter)

            logger.addHandler(file_handler)

    logger.propagate = False
    return logger


def get_logger(name: str | None = None) -> logging.Logger:
    """
    역할:
    INGEST 로깅 설정에서 재사용 리소스(로거/컬렉션/모델)를 조회 또는 생성합니다.
    
    Args:
    name (str | None):
    역할: `get_logger` 실행에 필요한 입력값입니다.
    값: 타입 힌트 기준 `str | None` 값이 전달됩니다.
    전달 출처: `INGEST 로깅 설정` 상위 호출부에서 전달됩니다.
    주의사항: 형식/범위가 함수 가정과 다르면 런타임 예외가 발생할 수 있습니다.
    
    Returns:
    logging.Logger: INGEST 로깅 설정 계산 결과를 `logging.Logger` 타입으로 반환합니다.
    
    Raises:
    Exception: 명시적 raise가 없어도 파일 I/O, 네트워크, 외부 라이브러리 예외가 전파될 수 있습니다.
    """

    base_logger = logging.getLogger("db_to_llm")
    if not base_logger.handlers:
        base_logger = setup_logger()

    if not name:
        return base_logger

    return base_logger.getChild(name)
