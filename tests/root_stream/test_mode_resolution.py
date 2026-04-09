# 이 파일은 mode 분기 관련 최소 규칙을 검증한다.
# API 입력 mode 별칭이 내부 mode 값으로 올바르게 변환되는지 확인한다.
# 오케스트레이터의 mode 검증 로직이 지원 범위를 벗어나면 실패하는지 확인한다.
# 외부 LLM 호출 없이 분기 로직만 테스트한다.

from __future__ import annotations

import unittest
from pathlib import Path

from Root_Stream.orchestrator.stream_orchestrator import StreamOrchestrator
from Root_Stream.services.query_service import resolve_internal_mode, to_public_mode


class ModeResolutionTests(unittest.TestCase):
    """mode 별칭/검증 테스트."""

    def test_resolve_internal_mode_alias(self) -> None:
        self.assertEqual(resolve_internal_mode("natural"), "natural_llm")
        self.assertEqual(resolve_internal_mode("prompt"), "prompt_llm")
        self.assertEqual(resolve_internal_mode("rag_prompt"), "rag_prompt_llm")

    def test_to_public_mode(self) -> None:
        self.assertEqual(to_public_mode("natural_llm"), "natural")
        self.assertEqual(to_public_mode("prompt_llm"), "prompt")
        self.assertEqual(to_public_mode("rag_prompt_llm"), "rag_prompt")

    def test_orchestrator_rejects_invalid_mode(self) -> None:
        orchestrator = StreamOrchestrator(
            config={"mode": "invalid_mode"},
            prompt_manager=None,  # type: ignore[arg-type]
            project_root=Path("."),
        )
        with self.assertRaises(ValueError):
            orchestrator._resolve_mode()


if __name__ == "__main__":
    unittest.main()
