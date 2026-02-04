# Schedule Assistant (일정 도우미) 설치 가이드

Slack에서 메시지를 보내면 Notion 일정을 확인하고 AI가 답변해주는 도우미예요.

## 이게 뭔가요?

Slack(팀 메신저)에서 "오늘 할 일이 뭐야?" 라고 물어보면,
Notion에 저장된 일정을 확인하고 AI가 대답해주는 시스템이에요.

## 준비물

1. **Python 3** (v3.9 이상)
   - 터미널에서 확인: `python3 --version`

2. **API 키 2개**
   - Notion API 키
   - OpenAI API 키

## 설치 방법

```bash
# 1. 이 폴더로 이동
cd skills/schedule-assistant

# 2. 환경 변수 파일 만들기
cp .env.example .env

# 3. .env 파일을 열고 API 키 입력
```

`.env` 파일 내용:

```
NOTION_API_KEY=ntn_여기에_Notion_API_키
OPENAI_API_KEY=sk-여기에_OpenAI_API_키
```

## API 키 발급 방법

### Notion API 키

1. [https://www.notion.so/my-integrations](https://www.notion.so/my-integrations) 접속
2. **새 통합(New integration)** 클릭 → 이름 입력 → 제출
3. 시크릿 키 복사 (`ntn_` 으로 시작)
4. Notion에서 일정 데이터베이스 페이지 열기
5. **···** → **연결(Connections)** → 만든 통합 추가

### OpenAI API 키

1. [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys) 접속
2. **Create new secret key** 클릭
3. 키 복사 (`sk-` 로 시작)

## 사용 방법

### 직접 실행

```bash
# 스크립트로 실행
./run.sh "오늘 할 일이 뭐야?"

# 또는 Python으로 직접 실행
python3 run.py "이번 주 일정 알려줘"
```

### n8n 워크플로우에서 호출

n8n의 SSH Execute Command 노드에서 이렇게 호출할 수 있어요:

```bash
/path/to/skills/schedule-assistant/run.sh "사용자 메시지"
```

## 파일 설명

| 파일 | 설명 |
|------|------|
| `run.py` | 메인 실행 파일 (Notion 조회 + AI 응답 생성) |
| `run.sh` | 실행 스크립트 (환경 설정 포함) |
| `config.json` | Notion 데이터베이스 ID 등 설정 |
| `.env.example` | 환경 변수 예제 파일 |

## 문제가 생겼을 때

| 문제 | 해결 방법 |
|------|-----------|
| 실행 권한 오류 | `chmod +x run.sh` 실행 |
| Notion 일정이 안 보여요 | Notion에 Integration 연결 확인 (위 4-5단계) |
| API 키 오류 | `.env` 파일에 키가 제대로 들어있는지 확인 |
