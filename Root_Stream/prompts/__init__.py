# 이 파일은 프롬프트 매니저를 외부 모듈에서 쉽게 import 하도록 돕습니다.
# 프롬프트 파일 위치와 로딩 책임은 PromptManager가 담당합니다.
# mode 서비스는 key 기반으로 프롬프트를 조회/렌더링합니다.
# 중앙 프롬프트 관리 원칙을 유지하기 위한 진입점입니다.

from Root_Stream.prompts.prompt_manager import PromptManager

__all__ = ["PromptManager"]
