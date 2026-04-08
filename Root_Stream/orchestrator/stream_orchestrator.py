# 이 파일은 STREAM 단계의 공통 진입 오케스트레이터를 담당합니다.

# config.mode를 읽어 4가지 실행 방식을 분기하고 결과 포맷을 통일합니다.

# 로깅/프롬프트/LLM 클라이언트 준비를 한 곳에서 처리해 중복을 줄입니다.

# 노트북/CLI/서비스가 동일한 실행 경로를 재사용하도록 설계했습니다.

from __future__ import annotations
from pathlib import Path
from typing import Any
from Root_Stream.prompts.prompt_manager import PromptManager
from Root_Stream.services.llm.llm_factory import create_llm_client
from Root_Stream.services.stream.mode_api_result import run_api_result_mode
from Root_Stream.services.stream.mode_natural_llm import run_natural_llm_mode
from Root_Stream.services.stream.mode_prompt_llm import run_prompt_llm_mode
from Root_Stream.services.stream.mode_rag_prompt_llm import run_rag_prompt_llm_mode
from Root_Stream.stream.models import StreamRequest, StreamResult
from Root_Stream.utils.config_loader import load_config
from Root_Stream.utils.logger import get_logger, setup_logger
from Root_Stream.utils.path_utils import resolve_path

logger = get_logger(__name__)

SUPPORTED_MODES = ("natural_llm", "prompt_llm", "rag_prompt_llm", "api_result")


class StreamOrchestrator:
    """config 기반 STREAM mode 오케스트레이터입니다."""

    def __init__(self, *, config: dict[str, Any], prompt_manager: PromptManager, project_root: Path) -> None:
        """
        역할:
        STREAM 오케스트레이션에 필요한 초기 속성과 의존성을 설정합니다.
        
        Args:
        config (dict[str, Any]):
        역할: 모드, provider, 경로, retrieval 등 런타임 설정을 참조합니다.
        값: YAML과 환경변수 오버라이드가 반영된 `dict[str, Any]`입니다.
        전달 출처: `load_config()` 결과가 전달됩니다.
        주의사항: 필수 키 누락 시 `KeyError` 또는 `ValueError`가 발생할 수 있습니다.
        prompt_manager (PromptManager):
        역할: 프롬프트 키 조회와 템플릿 렌더링을 수행합니다.
        값: `PromptManager` 인스턴스입니다.
        전달 출처: `build_stream_orchestrator()`에서 생성되어 전달됩니다.
        주의사항: 템플릿 변수 누락 시 `KeyError`가 발생할 수 있습니다.
        project_root (Path):
        역할: 상대 경로를 해석할 기준 프로젝트 루트입니다.
        값: `Path` 객체입니다.
        전달 출처: config의 `paths.project_root`를 `resolve_path()`로 해석한 값이 전달됩니다.
        주의사항: 루트가 잘못되면 로그, prompt, chroma 경로가 모두 어긋납니다.
        
        Returns:
        None: 반환값 없이 내부 상태 업데이트, 로깅, 파일 저장 같은 부수효과를 수행합니다.
        
        Raises:
        Exception: 명시적 raise가 없어도 파일 I/O, 네트워크, 외부 라이브러리 예외가 전파될 수 있습니다.
        """

        self.config = config

        self.prompt_manager = prompt_manager

        self.project_root = project_root

    def run(self, question: str) -> StreamResult:
        """
        역할:
        STREAM 오케스트레이션의 메인 실행 경로를 시작합니다.
        
        Args:
        question (str):
        역할: 사용자 자연어 질문 본문입니다.
        값: 일반 문자열입니다.
        전달 출처: CLI 인자 또는 API/노트북 호출부에서 전달됩니다.
        주의사항: 빈 문자열이면 프롬프트 품질이 크게 떨어지거나 검증 예외가 발생합니다.
        
        Returns:
        StreamResult: query, metadata, retrieved_context를 포함한 STREAM 표준 결과를 반환합니다.
        
        Raises:
        Exception: 명시적 raise가 없어도 파일 I/O, 네트워크, 외부 라이브러리 예외가 전파될 수 있습니다.
        """

        request = StreamRequest(question=question)
        return self.run_request(request)

    def run_request(self, request: StreamRequest) -> StreamResult:
        """
        역할:
        STREAM 오케스트레이션 흐름을 실행하고 후속 단계에서 사용할 결과를 조합해 반환합니다.
        
        Args:
        request (StreamRequest):
        역할: 사용자 질문을 포함한 STREAM 요청 모델입니다.
        값: `StreamRequest` 인스턴스입니다.
        전달 출처: `StreamOrchestrator.run()` 또는 테스트 코드에서 생성되어 전달됩니다.
        주의사항: `request.question`이 비어 있으면 하위 모드에서 오류가 날 수 있습니다.
        
        Returns:
        StreamResult: query, metadata, retrieved_context를 포함한 STREAM 표준 결과를 반환합니다.
        
        Raises:
        Exception: 내부 검증 실패 또는 하위 호출 오류 상황에서 발생할 수 있습니다.
        ValueError: 내부 검증 실패 또는 하위 호출 오류 상황에서 발생할 수 있습니다.
        """

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

            elif mode == "api_result":
                result = run_api_result_mode(

                    request=request,

                    config=self.config,

                    prompt_manager=self.prompt_manager,

                    llm_client=llm_client,

                )

            else:
                raise ValueError(f"지원하지 않는 mode입니다: {mode}")

        except Exception:
            logger.exception("STREAM 실행 실패: mode=%s", mode)

            raise

        logger.info("STREAM 실행 완료: mode=%s", mode)
        return result

    def _resolve_mode(self) -> str:
        """
        역할:
        STREAM 오케스트레이션에서 설정값을 검증 가능한 최종 값으로 확정합니다.
        
        Returns:
        str: 텍스트/프롬프트/SQL 문자열 결과를 반환합니다.
        
        Raises:
        ValueError: 내부 검증 실패 또는 하위 호출 오류 상황에서 발생할 수 있습니다.
        """

        mode = str(self.config.get("mode", "natural_llm")).strip().lower()
        if mode not in SUPPORTED_MODES:
            available = ", ".join(SUPPORTED_MODES)

            raise ValueError(f"지원하지 않는 mode입니다: {mode}. 사용 가능: {available}")

        return mode


def build_stream_orchestrator(config_path: Path) -> StreamOrchestrator:
    """
    역할:
    STREAM 오케스트레이션에서 사용할 객체를 설정값에 맞게 생성합니다.
    
    Args:
    config_path (Path):
    역할: 로드할 설정 파일 위치를 지정합니다.
    값: `Path` 형식의 파일 경로입니다.
    전달 출처: CLI `--config` 값 또는 상위 실행 코드에서 전달됩니다.
    주의사항: 상대 경로일 때 실행 위치에 따라 다른 파일을 읽을 수 있어 `resolve()` 결과 확인이 필요합니다.
    
    Returns:
    StreamOrchestrator: STREAM 오케스트레이션 계산 결과를 `StreamOrchestrator` 타입으로 반환합니다.
    
    Raises:
    Exception: 명시적 raise가 없어도 파일 I/O, 네트워크, 외부 라이브러리 예외가 전파될 수 있습니다.
    """

    config = load_config(config_path)

    stream_root = config_path.parent.parent

    project_root = resolve_path(config.get("paths", {}).get("project_root", "."), stream_root)

    _configure_logging(config=config, project_root=project_root)

    prompt_file_path = resolve_path(config["paths"]["prompt_file"], project_root)

    prompt_manager = PromptManager(prompt_file_path=prompt_file_path)
    return StreamOrchestrator(config=config, prompt_manager=prompt_manager, project_root=project_root)


def _configure_logging(config: dict[str, Any], project_root: Path) -> None:
    """
    역할:
    STREAM 오케스트레이션 문맥에서 `_configure_logging` 기능을 수행합니다.
    
    Args:
    config (dict[str, Any]):
    역할: 모드, provider, 경로, retrieval 등 런타임 설정을 참조합니다.
    값: YAML과 환경변수 오버라이드가 반영된 `dict[str, Any]`입니다.
    전달 출처: `load_config()` 결과가 전달됩니다.
    주의사항: 필수 키 누락 시 `KeyError` 또는 `ValueError`가 발생할 수 있습니다.
    project_root (Path):
    역할: 상대 경로를 해석할 기준 프로젝트 루트입니다.
    값: `Path` 객체입니다.
    전달 출처: config의 `paths.project_root`를 `resolve_path()`로 해석한 값이 전달됩니다.
    주의사항: 루트가 잘못되면 로그, prompt, chroma 경로가 모두 어긋납니다.
    
    Returns:
    None: 반환값 없이 내부 상태 업데이트, 로깅, 파일 저장 같은 부수효과를 수행합니다.
    
    Raises:
    Exception: 명시적 raise가 없어도 파일 I/O, 네트워크, 외부 라이브러리 예외가 전파될 수 있습니다.
    """

    log_level = str(config.get("logging", {}).get("level", "INFO"))

    log_file_value = config.get("paths", {}).get("log_file")

    log_file_path = resolve_path(log_file_value, project_root) if log_file_value else None

    setup_logger(log_level=log_level, log_file_path=log_file_path)
