# 이 파일은 Planner 결과를 해석할 때 사용하는 공통 상수 타입을 정의한다.
# 라우팅 규칙에서 문자열 하드코딩을 줄여 가독성과 안정성을 높인다.
# Graph 노드와 테스트가 같은 기준값을 공유하도록 단일 파일로 관리한다.
# 기존 Planner 모델의 query_type/type 값과 직접 호환되도록 구성한다.

from __future__ import annotations

QUERY_TYPES_DB = {"DB_ONLY", "DB_THEN_RAG", "DB_THEN_GENERAL"}
QUERY_TYPES_RAG = {"RAG_ONLY", "DB_THEN_RAG", "RAG_THEN_GENERAL"}
QUERY_TYPES_GENERAL = {"GENERAL", "DB_THEN_GENERAL", "RAG_THEN_GENERAL"}
STEP_TYPES = {"db", "rag", "general"}

