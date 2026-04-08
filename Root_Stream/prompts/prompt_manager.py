# 이 파일은 프롬프트 템플릿을 중앙에서 로딩/조회/렌더링하는 역할을 담당합니다.

# mode 코드에 프롬프트 문자열을 하드코딩하지 않도록 key 기반 접근을 제공합니다.

# 템플릿 변수 포맷팅 오류를 명확한 예외로 전달해 디버깅을 쉽게 합니다.

# YAML 기반 프롬프트 파일을 사용해 운영 중 프롬프트 교체를 단순화합니다.

from __future__ import annotations
from pathlib import Path
from typing import Any
import yaml
from Root_Stream.utils.logger import get_logger

logger = get_logger(__name__)


class PromptManager:
    """프롬프트 템플릿 로더/렌더러입니다."""

    def __init__(self, prompt_file_path: Path) -> None:
        """
        역할:
        프롬프트 템플릿 관리에 필요한 초기 속성과 의존성을 설정합니다.
        
        Args:
        prompt_file_path (Path):
        역할: 파일 또는 디렉터리 경로를 지정합니다.
        값: 타입 힌트 기준 `Path` 값이 전달됩니다.
        전달 출처: config 해석 결과 또는 이전 단계 계산 결과가 전달됩니다.
        주의사항: 상대 경로 기준이 다르면 의도하지 않은 위치를 참조할 수 있습니다.
        
        Returns:
        None: 반환값 없이 내부 상태 업데이트, 로깅, 파일 저장 같은 부수효과를 수행합니다.
        
        Raises:
        Exception: 명시적 raise가 없어도 파일 I/O, 네트워크, 외부 라이브러리 예외가 전파될 수 있습니다.
        """

        self.prompt_file_path = prompt_file_path

        self._prompts = self._load_prompts()

    def _load_prompts(self) -> dict[str, str]:
        """
        역할:
        프롬프트 템플릿 관리 문맥에서 `_load_prompts` 기능을 수행합니다.
        
        Returns:
        dict[str, str]: 프롬프트 템플릿 관리 단계에서 후속 처리에 바로 사용할 매핑 데이터를 반환합니다.
        
        Raises:
        FileNotFoundError: 내부 검증 실패 또는 하위 호출 오류 상황에서 발생할 수 있습니다.
        ValueError: 내부 검증 실패 또는 하위 호출 오류 상황에서 발생할 수 있습니다.
        """

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
        """
        역할:
        프롬프트 템플릿 관리에서 재사용 리소스(로거/컬렉션/모델)를 조회 또는 생성합니다.
        
        Args:
        prompt_key (str):
        역할: 사용할 템플릿 프롬프트 키를 지정합니다.
        값: 문자열 키 값입니다.
        전달 출처: config 또는 함수 내부 상수에서 전달됩니다.
        주의사항: 정의되지 않은 키면 `PromptManager.get_prompt()`에서 실패합니다.
        
        Returns:
        str: 텍스트/프롬프트/SQL 문자열 결과를 반환합니다.
        
        Raises:
        KeyError: 내부 검증 실패 또는 하위 호출 오류 상황에서 발생할 수 있습니다.
        """
        if prompt_key not in self._prompts:
            available = ", ".join(sorted(self._prompts))

            raise KeyError(f"프롬프트 키를 찾을 수 없습니다: {prompt_key}. 사용 가능 키: {available}")

        return self._prompts[prompt_key]

    def render_prompt(self, prompt_key: str, values: dict[str, Any] | None = None) -> str:
        """
        역할:
        프롬프트 템플릿 관리 문맥에서 `render_prompt` 기능을 수행합니다.
        
        Args:
        prompt_key (str):
        역할: 사용할 템플릿 프롬프트 키를 지정합니다.
        값: 문자열 키 값입니다.
        전달 출처: config 또는 함수 내부 상수에서 전달됩니다.
        주의사항: 정의되지 않은 키면 `PromptManager.get_prompt()`에서 실패합니다.
        values (dict[str, Any] | None):
        역할: 프롬프트 플레이스홀더를 치환할 값 묶음입니다.
        값: `dict[str, Any]` 또는 `None`입니다.
        전달 출처: mode 함수/노트북에서 질문과 컨텍스트를 조합해 전달합니다.
        주의사항: 필수 키를 누락하면 렌더링 오류가 발생할 수 있습니다.
        
        Returns:
        str: 텍스트/프롬프트/SQL 문자열 결과를 반환합니다.
        
        Raises:
        KeyError: 내부 검증 실패 또는 하위 호출 오류 상황에서 발생할 수 있습니다.
        """

        template = self.get_prompt(prompt_key)

        values = values or {}

        default_values = {

            "question": "",

            "schema_context": "",

            "retrieved_context": "",

            "business_rules": "",

            "additional_constraints": "",

            "api_result": "",

        }

        merged_values = {**default_values, **values}
        try:
            return template.format(**merged_values)

        except KeyError as error:
            missing_key = str(error).strip("'")

            raise KeyError(f"프롬프트 템플릿 변수 누락: key={prompt_key}, missing={missing_key}") from error

    def list_prompt_keys(self) -> list[str]:
        """
        역할:
        프롬프트 템플릿 관리 문맥에서 `list_prompt_keys` 기능을 수행합니다.
        
        Returns:
        list[str]: 프롬프트 템플릿 관리 결과를 순회 가능한 목록으로 반환합니다.
        
        Raises:
        Exception: 명시적 raise가 없어도 파일 I/O, 네트워크, 외부 라이브러리 예외가 전파될 수 있습니다.
        """
        return sorted(self._prompts.keys())
