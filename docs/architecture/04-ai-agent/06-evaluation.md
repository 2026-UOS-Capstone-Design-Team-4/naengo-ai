# 06. AI Evaluation

AI Agent 평가는 단위 테스트와 분리해 golden case의 품질 변화를 측정한다.
평가 데이터는 개인정보가 없는 curated case만 사용한다.

## Dataset

`evals/cases/chat_agent.yaml`은 50개 케이스를 포함한다.

- recipe find: 15
- cooking QA: 15
- allergy and safety: 10
- conversation context: 5
- profile and scope: 5

각 케이스는 입력, 기대 intent/routing/retrieval 계약, deterministic fixture 출력을
가진다. case id는 dataset 안에서 유일해야 한다.

## Modes

### Deterministic

```text
uv run python scripts/eval/run_agent_evals.py --mode deterministic
```

Pydantic Evals와 고정 fixture를 사용한다. 외부 LLM, embedding, DB를 호출하지
않으며 PR 필수 gate로 실행한다.

### Live

```text
uv run python scripts/eval/run_agent_evals.py --mode live
```

실제 agent 모델을 호출하되 retrieval은 case fixture로 고정한다. 응답은 별도
LLM judge가 relevance, usefulness, groundedness, safety를 각각 1~5점으로
평가한다. `EVAL_JUDGE_MODEL`이 없으면 `MODEL_NAME`을 judge에도 사용한다.

### Retrieval

```text
uv run python scripts/eval/run_agent_evals.py --mode retrieval --with-db
```

실제 PostgreSQL/pgvector 검색을 실행한다. 데이터 변경에 따라 결과가 달라질 수
있으므로 PR gate에는 포함하지 않는다.

## Baseline Policy

- safety violation과 evaluation error는 항상 0이어야 한다.
- intent, routing, retrieval 정확도가 baseline보다 2%p 초과 하락하면 실패한다.
- judge 평균이 0.2점 초과 하락하면 실패한다.
- 3점 미만 judge case가 2건 이상 증가하면 실패한다.
- latency와 token 사용량이 20% 초과 증가하면 warning을 기록한다.
- baseline은 `--update-baseline --baseline <path>`를 명시한 경우에만 갱신한다.

## Reports and CI

리포트는 `artifacts/evals/`에 JSON과 Markdown으로 생성하고 git에는 포함하지
않는다.

- `.github/workflows/test.yml`: Ruff, pytest, deterministic evaluation
- `.github/workflows/agent-eval.yml`: 수동 live/retrieval evaluation

수동 workflow는 `API_KEY`, `MODEL_NAME`, `EMBEDDING_API_KEY` secret이 필요하다.
retrieval mode는 `DATABASE_URL`도 필요하다.
