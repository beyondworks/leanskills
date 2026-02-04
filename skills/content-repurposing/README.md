# Content Repurposing (콘텐츠 재가공) 설치 가이드

YouTube 영상을 자동으로 블로그 글로 바꿔주는 도구예요.

## 이게 뭔가요?

유튜브 영상의 자막을 가져와서, AI가 읽기 좋은 블로그 글로 변환해줘요.
변환된 글은 Notion에 자동으로 저장됩니다.

**순서: YouTube 영상 → 자막 추출 → AI가 글 작성 → Notion에 저장**

## 준비물

1. **Python 3** (v3.9 이상)
   - Mac: 이미 설치되어 있을 수 있어요. 터미널에서 `python3 --version` 으로 확인
   - 없으면: [https://www.python.org/downloads](https://www.python.org/downloads)

2. **API 키 3개** (아래에서 발급 방법 설명)
   - Apify API 토큰 (유튜브 자막 가져오기용)
   - OpenAI API 키 (AI 글 작성용)
   - Notion API 키 (문서 저장용)

## 설치 방법

```bash
# 1. 이 폴더로 이동
cd skills/content-repurposing

# 2. 필요한 라이브러리 설치
pip install --user -r requirements.txt
```

## API 키 발급 방법

### Apify API 토큰

Apify는 유튜브 자막을 가져오는 서비스예요. 무료로 한 달에 약 1000번 사용할 수 있어요.

1. [https://console.apify.com](https://console.apify.com) 에 가입해요
2. 왼쪽 메뉴에서 **Settings > Integrations** 클릭
3. **Personal API tokens** 에서 토큰을 복사해요

### OpenAI API 키

OpenAI는 ChatGPT를 만든 회사예요. AI가 글을 쓸 때 사용해요.

1. [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys) 에 가입해요
2. **Create new secret key** 클릭
3. 키를 복사해요 (`sk-` 로 시작해요)

> **참고**: OpenAI API는 유료예요. 처음 가입하면 무료 크레딧을 줘요.

### Notion API 키

1. [https://www.notion.so/my-integrations](https://www.notion.so/my-integrations) 에 접속
2. **새 통합(New integration)** 클릭
3. 이름 정하고 **제출(Submit)**
4. 시크릿 키 복사 (`ntn_` 으로 시작)

## 설정 파일 만들기

```bash
# 예제 파일을 복사해서 설정 파일 만들기
cp notion_config.example.json notion_config.json
```

`notion_config.json` 파일을 열고 자신의 키를 넣어요:

```json
{
    "notion_api_key": "ntn_여기에_Notion_키",
    "openai_api_key": "sk-여기에_OpenAI_키",
    "apify_api_key": "apify_여기에_Apify_키",
    "categories": {
        "AI": "Notion_데이터베이스_ID",
        "Automation": "Notion_데이터베이스_ID"
    }
}
```

> **Notion 데이터베이스 ID 찾는 법**: Notion 페이지 URL에서 `?v=` 앞의 32자리 문자가 ID예요.

## 사용 방법

```bash
# YouTube 영상을 블로그 글로 변환
APIFY_API_TOKEN=apify_xxx OPENAI_API_KEY=sk-xxx python3 src/repurpose.py "https://www.youtube.com/watch?v=VIDEO_ID"
```

또는 실행 스크립트를 사용해요:

```bash
# 실행 권한 부여 (처음 한 번만)
chmod +x run_pipeline.sh

# 실행
./run_pipeline.sh "https://www.youtube.com/watch?v=VIDEO_ID"
```

## 파일 설명

| 파일 | 설명 |
|------|------|
| `src/repurpose.py` | 전체 파이프라인 (자막 → 글 → Notion 저장) |
| `src/fetch_transcript.py` | YouTube 자막 가져오기 |
| `src/blog_gen.py` | AI로 블로그 글 생성 |
| `src/daily_batch.py` | 여러 영상을 한꺼번에 처리 |
| `src/slack_notifier.py` | 처리 결과를 Slack으로 알림 |
| `requirements.txt` | 필요한 Python 라이브러리 목록 |
| `notion_config.example.json` | 설정 파일 예제 |

## 문제가 생겼을 때

| 문제 | 해결 방법 |
|------|-----------|
| `pip install` 오류 | `pip3 install --user -r requirements.txt` 로 시도해요 |
| Apify 오류 | API 토큰이 맞는지 확인해요 |
| Notion 저장 안 됨 | Notion 페이지에 Integration이 연결되어 있는지 확인해요 |
| 자막이 없는 영상 | 자막이 있는 영상만 처리할 수 있어요 |
