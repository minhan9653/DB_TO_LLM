# 이 파일은 STREAM 오케스트레이터의 공통 실행 흐름을 담당합니다.
# config에서 mode를 읽어 적절한 mode 실행 함수로 분기합니다.
# 서버/CLI에서 동일한 진입점을 재사용해 동작 일관성을 유지합니다.
# 로깅 설정, 프롬프트 로딩, 경로 해석을 한곳에서 초기화합니다.

from __future__ import annotations

from pathlib import Path
from typing import Any

from Root_Stream.prompts.prompt_manager import PromptManager
from Root_Stream.services.llm.llm_factory import create_llm_client
from Root_Stream.services.stream.mode_natural_llm import run_natural_llm_mode
from Root_Stream.services.stream.mode_prompt_llm import run_prompt_llm_mode
from Root_Stream.services.stream.mode_rag_prompt_llm import run_rag_prompt_llm_mode
from Root_Stream.stream.models import StreamRequest, StreamResult
from Root_Stream.utils.config_loader import load_config
from Root_Stream.utils.logger import get_logger, setup_logger
from Root_Stream.utils.path_utils import resolve_path

logger = get_logger(__name__)

SUPPORTED_MODES = ("natural_llm", "prompt_llm", "rag_prompt_llm")


class StreamOrchestrator:
    """STREAM mode 실행을 조율하는 오케스트레이터입니다."""

    def __init__(self, *, config: dict[str, Any], prompt_manager: PromptManager, project_root: Path) -> None:
        """실행에 필요한 설정과 의존 객체를 초기화합니다."""
        self.config = config
        self.prompt_manager = prompt_manager
        self.project_root = project_root

    def run(self, question: str) -> StreamResult:
        """문자열 질문을 StreamRequest로 감싼 뒤 실행합니다."""
        request = StreamRequest(question=question)
        return self.run_request(request)

    def run_request(self, request: StreamRequest) -> StreamResult:
        """mode 값에 맞는 실행 함수를 호출해 SQL 생성 결과를 반환합니다."""
        mode = self._resolve_mode()
        logger.info("STREAM 실행 시작: mode=%s", mode)

        try:
            llm_client = create_llm_client(self.config)

            if mode == "natural_llm":
                result = run_natural_llm_mode(
                    request=request,
                    config=self.config,
                    prompt_manager=self.prompt_manager,
                    llm_client=llm_client,
                )
            elif mode == "prompt_llm":
                result = run_prompt_llm_mode(
                    request=request,
                    config=self.config,
                    prompt_manager=self.prompt_manager,
                    llm_client=llm_client,
                )
            elif mode == "rag_prompt_llm":
                result = run_rag_prompt_llm_mode(
                    request=request,
                    config=self.config,
                    prompt_manager=self.prompt_manager,
                    llm_client=llm_client,
                    project_root=self.project_root,
                )
            else:
                raise ValueError(f"지원하지 않는 mode입니다: {mode}")
        except Exception:
            logger.exception("STREAM 실행 실패: mode=%s", mode)
            raise

        logger.info("STREAM 실행 완료: mode=%s", mode)
        return result

    def _resolve_mode(self) -> str:
        """config.mode 값을 검증해 내부 실행 mode를 반환합니다."""
        mode = str(self.config.get("mode", "natural_llm")).strip().lower()
        if mode not in SUPPORTED_MODES:
            available = ", ".join(SUPPORTED_MODES)
            raise ValueError(f"지원하지 않는 mode입니다: {mode}. 사용 가능 값: {available}")
        return mode


def build_stream_orchestrator(config_path: Path) -> StreamOrchestrator:
    """config 파일을 읽어 StreamOrchestrator를 생성합니다."""
    config = load_config(config_path)
    stream_root = config_path.parent.parent
    project_root = resolve_path(config.get("paths", {}).get("project_root", "."), stream_root)

    _configure_logging(config=config, project_root=project_root)

    prompt_file_path = resolve_path(config["paths"]["prompt_file"], project_root)
    prompt_manager = PromptManager(prompt_file_path=prompt_file_path)
    return StreamOrchestrator(config=config, prompt_manager=prompt_manager, project_root=project_root)


def _configure_logging(config: dict[str, Any], project_root: Path) -> None:
    """config의 로깅 설정을 읽어 공통 logger를 초기화합니다."""
    log_level = str(config.get("logging", {}).get("level", "INFO"))
    log_file_value = config.get("paths", {}).get("log_file")
    log_file_path = resolve_path(log_file_value, project_root) if log_file_value else None
    setup_logger(log_level=log_level, log_file_path=log_file_path)

