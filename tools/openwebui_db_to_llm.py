"""
title: DB_TO_LLM Query Tool
author: minhan9653
version: 1.0.0
license: MIT
description: >
  DB_TO_LLM API 서버에 자연어 질문을 보내고 결과를 반환하는 Open WebUI 도구.
  질문 유형(DB_ONLY / RAG_ONLY / DB_THEN_RAG / GENERAL)을 자동 판별하여
  SQL 조회, 문서 검색, 또는 일반 답변을 수행한다.
"""

from __future__ import annotations

from typing import Any

import requests
from pydantic import BaseModel, Field


class Tools:
    """DB_TO_LLM API 연동 도구."""

    class Valves(BaseModel):
        """Open WebUI에서 사용자가 설정할 수 있는 값."""

        server_url: str = Field(
            default="http://localhost:8000",
            description="DB_TO_LLM API 서버 주소 (예: http://192.168.0.10:8000)",
        )
        timeout: int = Field(
            default=120,
            description="API 요청 타임아웃 (초)",
        )
        show_sql: bool = Field(
            default=True,
            description="응답에 생성된 SQL 쿼리 포함 여부",
        )
        show_trace: bool = Field(
            default=False,
            description="응답에 실행 추적 로그 포함 여부",
        )

    def __init__(self):
        self.valves = self.Valves()

    def query(self, question: str) -> str:
        """
        자연어 질문을 DB_TO_LLM 시스템에 전달하고 최종 답변을 반환한다.
        DB 조회, 문서 검색(RAG), 또는 일반 질의응답을 자동으로 처리한다.

        :param question: 사용자의 자연어 질문
        :return: 최종 답변 (SQL, DB 결과, RAG 컨텍스트 포함 가능)
        """
        url = f"{self.valves.server_url.rstrip('/')}/api/query"

        try:
            response = requests.post(
                url,
                json={"question": question},
                timeout=self.valves.timeout,
            )
            response.raise_for_status()
        except requests.exceptions.ConnectionError:
            return f"[오류] DB_TO_LLM 서버에 연결할 수 없습니다: {self.valves.server_url}\n서버가 실행 중인지 확인하세요."
        except requests.exceptions.Timeout:
            return f"[오류] 요청 시간 초과 ({self.valves.timeout}초). 서버 응답이 너무 느립니다."
        except requests.exceptions.HTTPError as e:
            return f"[오류] 서버 응답 오류: {e.response.status_code} - {e.response.text}"
        except Exception as e:
            return f"[오류] 예상치 못한 오류 발생: {e}"

        data: dict[str, Any] = response.json()

        return self._format_response(data)

    def _format_response(self, data: dict[str, Any]) -> str:
        """API 응답을 사람이 읽기 좋은 형식으로 변환한다."""
        lines: list[str] = []

        query_type = data.get("query_type", "")
        lines.append(f"**[처리 유형]** {query_type}\n")

        # SQL 쿼리
        if self.valves.show_sql:
            sql = data.get("validated_sql") or data.get("generated_sql")
            if sql:
                validation_passed = data.get("sql_validation_passed", False)
                status = "✅ 검증 통과" if validation_passed else "⚠️ 검증 실패"
                lines.append(f"**[생성된 SQL]** ({status})")
                lines.append(f"```sql\n{sql}\n```")

        # DB 실행 결과
        db_rows: list[dict] = data.get("db_rows", [])
        db_columns: list[str] = data.get("db_columns", [])
        row_count = data.get("db_row_count", len(db_rows))
        if db_rows:
            lines.append(f"**[DB 조회 결과]** 총 {row_count}행")
            if not db_columns and db_rows:
                db_columns = list(db_rows[0].keys())
            if db_columns:
                header = " | ".join(db_columns)
                separator = " | ".join(["---"] * len(db_columns))
                lines.append(f"| {header} |")
                lines.append(f"| {separator} |")
                for row in db_rows[:50]:  # 최대 50행
                    values = " | ".join(str(row.get(c, "")) for c in db_columns)
                    lines.append(f"| {values} |")
                if row_count > 50:
                    lines.append(f"_(이하 {row_count - 50}행 생략)_")
            lines.append("")

        # DB 요약
        if data.get("db_summary"):
            lines.append(f"**[DB 요약]**\n{data['db_summary']}\n")

        # RAG 컨텍스트
        contexts: list[dict] = data.get("retrieved_contexts", [])
        if contexts:
            lines.append(f"**[참조 문서]** {len(contexts)}개 검색됨")
            for i, ctx in enumerate(contexts[:3], 1):
                source = ctx.get("source", "N/A")
                snippet = ctx.get("text", "")[:150]
                lines.append(f"  {i}. `{source}` — {snippet}...")
            lines.append("")

        # 최종 답변
        final_answer = data.get("final_answer", "(답변 없음)")
        lines.append(f"**[최종 답변]**\n{final_answer}")

        # 오류
        errors: list[str] = data.get("errors", [])
        if errors:
            lines.append("\n**[오류]**")
            for err in errors:
                lines.append(f"- {err}")

        # 추적 로그 (옵션)
        if self.valves.show_trace:
            trace: list[str] = data.get("trace_logs", [])
            if trace:
                lines.append("\n**[실행 로그]**")
                for log in trace:
                    lines.append(f"- {log}")

        return "\n".join(lines)
