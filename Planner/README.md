# Planner

## 목적
`Planner`는 사용자 질문을 실행 계획(JSON plan)으로 분해하는 독립 실험 모듈입니다.

## 현재 범위
- 질문 입력
- Planner 프롬프트 조합
- 기존 Root_Stream LLM 호출 구조 재사용
- JSON 응답 파싱
- 최소 형식 검증

## 현재 범위에서 제외
- DB 실행
- SQL 생성
- RAG 검색 실행
- FastAPI 연동

## 구성 파일
- `models.py`: Planner 데이터 모델(`PlannerPlan`, `PlannerStep`, `PlannerRunResult`)
- `planner_prompt.py`: `Root_Stream/prompts/prompt_templates.yaml`의 planner 프롬프트 로딩/렌더링
- `planner_service.py`: 설정 로딩 + LLM 호출 + JSON 파싱 + 검증을 담당하는 서비스
- `plan_validator.py`: Planner JSON 최소 형식 검증
- `debug_planner.py`: 수동 실행 스크립트
- `tests/test_planner_live.py`: 실제 LLM 호출 기반 pytest 테스트
- `notebooks/planner_llm_test.ipynb`: 노트북 실험 환경

## 실행 방법
### 1) 디버그 스크립트 실행
프로젝트 루트(`DB_TO_LLM`)에서 실행:

```bash
python Planner/debug_planner.py
```

질문을 직접 지정해서 실행:

```bash
python Planner/debug_planner.py --question "최근 30일간 가장 많이 발생한 알람을 찾고 해당 알람의 정의와 조치 방법을 알려줘"
```

### 2) pytest 실행 (실제 LLM 호출)
프로젝트 루트에서 실행:

```bash
python -m pytest Planner/tests/test_planner_live.py -s
```

`pytest`가 없다면 먼저 설치:

```bash
python -m pip install pytest
```

### 3) Notebook 실행
`Planner/notebooks/planner_llm_test.ipynb`를 열고 셀을 위에서부터 순서대로 실행합니다.
노트북 내부에서도 `PlannerService`를 import해 동일 서비스 로직을 재사용합니다.

## 통합 방향
현재 구조는 Root_Stream과 독립 실행되지만, 추후 Root_Stream 내부로 흡수할 때 다음 방식으로 이전하기 쉽도록 설계했습니다.
- `planner_prompt.py`는 기존 `PromptManager`를 그대로 사용
- `planner_service.py`는 기존 `load_config`, `create_llm_client` 재사용
- `plan_validator.py`는 순수 검증 모듈로 분리되어 mode 체인에 쉽게 삽입 가능
