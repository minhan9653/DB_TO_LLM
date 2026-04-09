# 이 파일은 프롬프트 템플릿을 YAML에서 읽어 key 기반으로 제공한다.
# mode 코드에서 긴 프롬프트 문자열을 하드코딩하지 않도록 중앙 관리한다.
# 템플릿 변수 치환 실패를 명확한 예외로 전달해 디버깅을 단순화한다.
# Root_Stream의 모든 모드와 Planner가 같은 매니저를 재사용한다.

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from Root_Stream.utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_TEMPLATE_VALUES = {
    "question": "",
    "schema_context": "",
    "retrieved_context": "",
    "business_rules": "",
    "additional_constraints": "",
}


class PromptManager:
    """프롬프트 파일 로딩/조회/렌더링을 담당한다."""

    def __init__(self, prompt_file_path: Path) -> None:
        self.prompt_file_path = prompt_file_path
        self._prompts = self._load_prompts()

    def _load_prompts(self) -> dict[str, str]:
        logger.info("프롬프트 파일 로드 시작: %s", self.prompt_file_path)
        if not self.prompt_file_path.exists():
            raise FileNotFoundError(f"프롬프트 파일이 없습니다: {self.prompt_file_path}")

        with self.prompt_file_path.open("r", encoding="utf-8") as file:
            payload: dict[str, Any] = yaml.safe_load(file) or {}

        prompts = payload.get("prompts", {})
        if not isinstance(prompts, dict):
            raise ValueError("prompts 항목은 dict 형식이어야 합니다.")

        normalized = {str(key): str(value) for key, value in prompts.items()}
        logger.info("프롬프트 파일 로드 완료: prompt_count=%d", len(normalized))
        return normalized

    def get_prompt(self, prompt_key: str) -> str:
        """키로 프롬프트 원문을 조회한다."""
        if prompt_key not in self._prompts:
            available = ", ".join(sorted(self._prompts))
            raise KeyError(f"프롬프트 키를 찾을 수 없습니다: {prompt_key}. 사용 가능 키: {available}")
        return self._prompts[prompt_key]

    def render_prompt(self, prompt_key: str, values: dict[str, Any] | None = None) -> str:
        """템플릿 프롬프트를 values로 치환해 반환한다."""
        template = self.get_prompt(prompt_key)
        merged_values = {**DEFAULT_TEMPLATE_VALUES, **(values or {})}
        try:
            return template.format(**merged_values)
        except KeyError as error:
            missing_key = str(error).strip("'")
            raise KeyError(f"프롬프트 템플릿 변수 누락: key={prompt_key}, missing={missing_key}") from error

    def list_prompt_keys(self) -> list[str]:
        """사용 가능한 프롬프트 키 목록을 반환한다."""
        return sorted(self._prompts.keys())
