# 이 파일은 prompt_templates.yaml에서 프롬프트를 읽어 키 기반으로 제공한다.
# 긴 프롬프트 문자열을 코드에 하드코딩하지 않도록 YAML 파일을 중앙 관리한다.
# 템플릿 변수({question} 등) 치환 실패를 명확한 예외로 전달해 디버깅을 돕는다.
# planner, sql 생성, rag 검색, 최종 답변 등 모든 노드가 이 매니저를 공통으로 사용한다.

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from src.db_to_llm.shared.logging.logger import get_logger

logger = get_logger(__name__)

# 프롬프트 템플릿의 기본 치환 변수 (누락 시 빈 문자열로 대체)
DEFAULT_TEMPLATE_VALUES: dict[str, str] = {
    "question": "",
    "schema_context": "",
    "retrieved_context": "",
    "business_rules": "",
    "additional_constraints": "",
    "db_summary": "",
    "row_count": "",
    "columns": "",
    "sample_rows": "",
}

# 이 파일과 같은 디렉터리에 있는 prompt_templates.yaml을 기본 경로로 사용
DEFAULT_PROMPT_FILE = Path(__file__).parent / "prompt_templates.yaml"


class PromptManager:
    """YAML 파일에서 프롬프트 템플릿을 읽어 키 기반으로 조회하고 렌더링한다."""

    def __init__(self, prompt_file_path: Path | None = None) -> None:
        """
        PromptManager를 초기화하고 프롬프트 파일을 로드한다.

        Args:
            prompt_file_path: 프롬프트 YAML 파일 경로. None이면 기본 경로를 사용한다.
        """
        self.prompt_file_path = prompt_file_path or DEFAULT_PROMPT_FILE
        self._prompts = self._load_prompts()

    def _load_prompts(self) -> dict[str, str]:
        """YAML 파일을 읽어 prompts 섹션을 dict로 반환한다."""
        logger.info("프롬프트 파일 로드 시작: %s", self.prompt_file_path)

        if not self.prompt_file_path.exists():
            raise FileNotFoundError(f"프롬프트 파일이 없습니다: {self.prompt_file_path}")

        with self.prompt_file_path.open("r", encoding="utf-8") as file:
            payload: dict[str, Any] = yaml.safe_load(file) or {}

        prompts = payload.get("prompts", {})
        if not isinstance(prompts, dict):
            raise ValueError("prompt_templates.yaml의 prompts 항목은 dict 형식이어야 합니다.")

        normalized = {str(key): str(value) for key, value in prompts.items()}
        logger.info("프롬프트 로드 완료: %d개 키", len(normalized))
        return normalized

    def get_prompt(self, prompt_key: str) -> str:
        """
        키에 해당하는 프롬프트 원문을 반환한다.

        Args:
            prompt_key: 조회할 프롬프트 키. 예: "query_generation_prompt"

        Returns:
            str: 프롬프트 템플릿 원문.

        Raises:
            KeyError: 해당 키가 없으면 사용 가능한 키 목록을 포함한 오류를 발생시킨다.
        """
        if prompt_key not in self._prompts:
            available_keys = ", ".join(sorted(self._prompts.keys()))
            raise KeyError(
                f"프롬프트 키를 찾을 수 없습니다: '{prompt_key}'. "
                f"사용 가능한 키: {available_keys}"
            )
        return self._prompts[prompt_key]

    def render_prompt(self, prompt_key: str, values: dict[str, Any] | None = None) -> str:
        """
        템플릿 프롬프트의 변수를 values로 치환해 최종 프롬프트를 반환한다.

        Args:
            prompt_key: 사용할 프롬프트 키.
            values: 템플릿 변수와 치환 값의 dict. None이면 기본값만 사용한다.

        Returns:
            str: 변수가 치환된 최종 프롬프트 문자열.

        Raises:
            KeyError: 템플릿에 있는 변수가 values에도 기본값에도 없는 경우 발생한다.
        """
        template = self.get_prompt(prompt_key)
        # 기본값 위에 실제 값을 덮어쓴다
        merged_values = {**DEFAULT_TEMPLATE_VALUES, **(values or {})}

        try:
            return template.format(**merged_values)
        except KeyError as error:
            missing_key = str(error).strip("'")
            raise KeyError(
                f"프롬프트 템플릿 변수 누락: key='{prompt_key}', missing='{missing_key}'"
            ) from error

    def list_prompt_keys(self) -> list[str]:
        """사용 가능한 모든 프롬프트 키 목록을 정렬해 반환한다."""
        return sorted(self._prompts.keys())
