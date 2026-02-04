# Leanskills - AI 자동화 도구 모음

AI 도우미(Claude, Cursor)와 n8n 워크플로우 자동화를 위한 도구 모음이에요.

이 레포를 다운받으면, 선생님과 똑같은 AI 자동화 환경을 세팅할 수 있어요!

---

## 이 레포에 뭐가 있나요?

```
leanskills/
├── mcp/                         ← AI 도우미 연결 도구
│   ├── n8n-mcp/                 ← n8n 자동화 연결
│   └── notion-mcp/              ← Notion 문서 연결
├── skills/                      ← AI 스킬 (Python 프로그램)
│   ├── content-repurposing/     ← YouTube → 블로그 글 자동 변환
│   ├── schedule-assistant/      ← 일정 관리 도우미
│   └── beyondworks-assistant/   ← 비즈니스 AI 도우미
├── workflows/                   ← n8n 워크플로우 파일
│   ├── scripts/                 ← 배포 스크립트
│   ├── schedule-assistant/      ← 일정 도우미 워크플로우
│   └── beyondworks-assistant/   ← 비즈니스 도우미 워크플로우
└── n8n-reference/               ← n8n 참조 문서
```

---

## 처음 시작하기 (따라 하세요!)

### 1단계: 필요한 프로그램 설치

아래 프로그램들이 컴퓨터에 있어야 해요. 없으면 링크를 클릭해서 설치해요.

| 프로그램 | 설명 | 다운로드 |
|----------|------|----------|
| **Node.js** | JavaScript 실행기 (MCP에 필요) | [nodejs.org](https://nodejs.org) |
| **Python 3** | 프로그래밍 언어 (스킬에 필요) | [python.org](https://www.python.org/downloads) |
| **Git** | 코드 다운로드 도구 | [git-scm.com](https://git-scm.com) |

설치가 됐는지 확인하는 방법 (터미널에서 입력):

```bash
node --version    # v18.0.0 이상이면 OK
python3 --version # 3.9 이상이면 OK
git --version     # 아무 버전이나 나오면 OK
```

### 2단계: 이 레포 다운로드

```bash
git clone https://github.com/beyondworks/leanskills.git
cd leanskills
```

### 3단계: 원하는 도구 설정

아래에서 사용하고 싶은 도구를 골라서 설치해요. 전부 다 할 필요는 없어요!

---

## MCP 설정 (AI 도우미 연결)

MCP는 AI 도우미가 외부 서비스를 사용할 수 있게 해주는 도구예요.

| MCP | 뭘 할 수 있나요? | 설치 가이드 |
|-----|-----------------|-------------|
| **n8n-MCP** | AI가 n8n 워크플로우를 만들고 관리해요 | [설치 가이드 보기](./mcp/n8n-mcp/README.md) |
| **Notion MCP** | AI가 Notion 문서를 읽고 써요 | [설치 가이드 보기](./mcp/notion-mcp/README.md) |

MCP 전체 설명은 [mcp/README.md](./mcp/README.md)를 읽어보세요.

---

## Skills 설정 (AI 스킬)

스킬은 특정 작업을 자동으로 해주는 Python 프로그램이에요.

| 스킬 | 뭘 해주나요? | 필요한 API | 설치 가이드 |
|------|-------------|-----------|-------------|
| **content-repurposing** | YouTube 영상 → 블로그 글 → Notion 저장 | Apify, OpenAI, Notion | [설치 가이드](./skills/content-repurposing/README.md) |
| **schedule-assistant** | Slack에서 일정 관리 | OpenAI, Notion | [설치 가이드](./skills/schedule-assistant/SETUP.md) |
| **beyondworks-assistant** | 멀티도메인 비즈니스 도우미 | OpenAI, Notion | [설치 가이드](./skills/beyondworks-assistant/SETUP.md) |

스킬 전체 설명은 [skills/README.md](./skills/README.md)를 읽어보세요.

---

## Workflows (n8n 워크플로우)

워크플로우는 n8n에서 사용하는 자동화 설정 파일이에요. JSON 파일로 되어 있어요.

### 워크플로우 가져오기 (Import)

1. n8n 웹사이트에 접속해요 (보통 `http://localhost:5678`)
2. 왼쪽 메뉴에서 **워크플로우** 클릭
3. 오른쪽 위 **⋯** → **Import from File** 클릭
4. `workflows/` 폴더에서 원하는 JSON 파일을 선택해요

### 포함된 워크플로우

| 워크플로우 | 설명 |
|------------|------|
| `daily-news-clipping.json` | 매일 뉴스를 모아주는 자동화 |
| `ai-email-support-kr.json` | AI 이메일 고객 응대 |
| `finance-news-kr.json` | 금융 뉴스 수집 |
| `google-maps-lead-kr.json` | Google Maps 리드 수집 |
| `mistral-ocr-kr.json` | Mistral OCR 문서 인식 |
| `notion-slack-schedule-assistant.json` | Notion+Slack 일정 관리 |

---

## API 키 발급 총정리

여러 도구에서 공통으로 사용하는 API 키 발급 방법을 정리했어요.

### Notion API 키

1. [https://www.notion.so/my-integrations](https://www.notion.so/my-integrations) 접속
2. **새 통합(New integration)** 클릭
3. 이름 입력 → 워크스페이스 선택 → **제출**
4. 시크릿 키 복사 (`ntn_` 으로 시작하는 긴 글자)
5. AI가 접근할 Notion 페이지에서 **···** → **연결** → 만든 통합 추가

### OpenAI API 키

1. [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys) 접속
2. **Create new secret key** 클릭
3. 키 복사 (`sk-` 로 시작)
4. 결제 수단 등록 필요 (처음 가입 시 무료 크레딧 제공)

### Apify API 토큰

1. [https://console.apify.com](https://console.apify.com) 가입
2. **Settings > Integrations** → 토큰 복사
3. 무료 티어로 한 달 약 1000번 사용 가능

### n8n API 키

1. n8n 웹사이트 접속 (보통 `http://localhost:5678`)
2. **설정(Settings)** → **API** → **Create API Key**
3. 키 복사

---

## 주의사항

- **API 키는 비밀번호와 같아요!** GitHub에 올리거나 다른 사람에게 보여주면 안 돼요.
- `.env` 파일과 `notion_config.json` 같은 설정 파일은 `.gitignore`에 의해 자동으로 GitHub에 올라가지 않아요.
- 이 레포에 포함된 `.env.example` 파일을 `.env`로 복사해서 자신의 키를 넣어 사용해요.

---

## 문제가 생겼을 때

| 문제 | 확인할 것 |
|------|-----------|
| `node: command not found` | Node.js 설치 확인 |
| `python3: command not found` | Python 설치 확인 |
| `git: command not found` | Git 설치 확인 |
| API 키 오류 | 키를 제대로 복사했는지, 공백이 없는지 확인 |
| Notion 데이터가 안 보여요 | Notion 페이지에 Integration 연결 확인 |
| n8n 연결 안 됨 | n8n 서버가 실행 중인지 확인 (`http://localhost:5678`) |

더 자세한 도움이 필요하면 각 폴더의 README를 확인하거나, 선생님에게 질문해주세요!

---

## 관련 레포

| 레포 | 설명 |
|------|------|
| [beyondworks/n8n](https://github.com/beyondworks/n8n) | n8n 인스턴스 소프트웨어 (Docker 배포 포함) |
| [beyondworks/leanskills](https://github.com/beyondworks/leanskills) | 이 레포! (워크플로우, 스킬, MCP 설정) |
