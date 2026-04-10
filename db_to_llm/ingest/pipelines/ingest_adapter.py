# 이 파일은 기존 Root_Ingest 파이프라인을 신규 패키지 구조에서 호출하기 위한 어댑터다.
# 핵심 ingest 로직은 변경하지 않고 진입점만 통일해 재사용성을 높인다.
# Notebook/CLI에서 동일 함수 호출 방식으로 ingest를 실행할 수 있도록 단순 API를 제공한다.
# 구성 변경은 config 파일로 처리하고 코드 내부 하드코딩을 피한다.

from __future__ import annotations

from pathlib import Path
from typing import Any

from Root_Ingest.ingest.ingest_pipeline import run_ingest_pipeline


def run_ingest(config_path: str | Path) -> dict[str, Any]:
    """
    기존 Root_Ingest 파이프라인을 실행한다.

    Args:
        config_path: ingest config 파일 경로.

    Returns:
        dict[str, Any]: ingest 요약 결과.
    """
    return run_ingest_pipeline(Path(config_path).resolve())

