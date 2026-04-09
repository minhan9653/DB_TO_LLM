# 이 파일은 PromptManager의 로딩/렌더링 동작을 검증한다.
# 템플릿 변수 치환과 기본값 처리 규칙이 깨지지 않는지 확인한다.
# 임시 YAML 파일을 사용해 테스트가 저장소 실제 프롬프트에 의존하지 않게 유지한다.
# 외부 시스템 호출 없이 순수 함수 동작만 검증한다.

from __future__ import annotations

import unittest
from pathlib import Path

from Root_Stream.prompts.prompt_manager import PromptManager


class PromptManagerTests(unittest.TestCase):
    """PromptManager 테스트."""

    def test_render_prompt_replaces_values(self) -> None:
        prompt_path = Path(__file__).resolve().parent / "_runtime_prompts_1.yaml"
        prompt_path.write_text(
            "\n".join(
                [
                    "prompts:",
                    "  test_prompt: |",
                    "    Q: {question}",
                    "    S: {schema_context}",
                ]
            ),
            encoding="utf-8",
        )

        try:
            manager = PromptManager(prompt_file_path=prompt_path)
            rendered = manager.render_prompt(
                "test_prompt",
                {"question": "질문", "schema_context": "스키마"},
            )
        finally:
            prompt_path.unlink(missing_ok=True)

        self.assertIn("Q: 질문", rendered)
        self.assertIn("S: 스키마", rendered)

    def test_render_prompt_uses_default_values(self) -> None:
        prompt_path = Path(__file__).resolve().parent / "_runtime_prompts_2.yaml"
        prompt_path.write_text(
            "\n".join(
                [
                    "prompts:",
                    "  test_prompt: |",
                    "    Q: {question}",
                    "    R: {retrieved_context}",
                ]
            ),
            encoding="utf-8",
        )

        try:
            manager = PromptManager(prompt_file_path=prompt_path)
            rendered = manager.render_prompt("test_prompt", {"question": "A"})
        finally:
            prompt_path.unlink(missing_ok=True)

        self.assertIn("Q: A", rendered)
        self.assertIn("R: ", rendered)


if __name__ == "__main__":
    unittest.main()
