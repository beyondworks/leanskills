# Beyondworks Assistant (비즈니스 도우미) 설치 가이드

비즈니스, 콘텐츠, 재무, 일정, 여행 등 여러 분야를 관리해주는 AI 도우미예요.

## 이게 뭔가요?

Notion에 저장된 다양한 정보를 AI가 읽고 분석해줘요.
비즈니스 계획, 콘텐츠 관리, 재무 정보, 일정 관리, 여행 계획 등 여러 분야를 하나의 도우미가 처리해요.

## 준비물

1. **Python 3** (v3.9 이상)
   - 터미널에서 확인: `python3 --version`

2. **API 키 2개**
   - Notion API 키
   - OpenAI API 키

## 설치 방법

```bash
# 1. 이 폴더로 이동
cd skills/beyondworks-assistant

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
4. Notion에서 사용할 페이지들 열기
5. **···** → **연결(Connections)** → 만든 통합 추가

### OpenAI API 키

1. [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys) 접속
2. **Create new secret key** 클릭
3. 키 복사 (`sk-` 로 시작)

## 사용 방법

```bash
python3 assistant.py
```

실행하면 대화형으로 질문할 수 있어요:

```
> 이번 달 재무 현황을 알려줘
> 다음 주 콘텐츠 계획은?
> 출장 일정을 정리해줘
```

## 지원하는 분야

| 분야 | 설명 |
|------|------|
| 비즈니스 | 사업 계획, 프로젝트 관리 |
| 콘텐츠 | 블로그, 유튜브 콘텐츠 계획 |
| 재무 | 수입/지출, 재무 현황 |
| 일정 | 미팅, 일정 관리 |
| 여행 | 출장/여행 계획 |

## 파일 설명

| 파일 | 설명 |
|------|------|
| `assistant.py` | 메인 실행 파일 |
| `config.json` | Notion 데이터베이스 ID 등 설정 |
| `core/` | 핵심 기능 (Notion 연결, AI 처리) |
| `domains/` | 각 분야별 처리 로직 |
| `.env.example` | 환경 변수 예제 파일 |

## 문제가 생겼을 때

| 문제 | 해결 방법 |
|------|-----------|
| 모듈 못 찾음 오류 | `pip install openai notion-client` 실행 |
| Notion 데이터 안 보임 | Notion 페이지에 Integration 연결 확인 |
| API 키 오류 | `.env` 파일에 키가 제대로 들어있는지 확인 |
