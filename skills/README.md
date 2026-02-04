# Skills (스킬) 가이드

스킬은 AI 도우미가 특정 작업을 수행할 수 있게 해주는 Python 프로그램이에요.

## 포함된 스킬

| 스킬 | 설명 | 필요한 API |
|------|------|-----------|
| [content-repurposing](./content-repurposing/) | YouTube 영상 → 블로그 글 → Notion 저장 | Apify, OpenAI, Notion |
| [schedule-assistant](./schedule-assistant/) | Slack 메시지로 Notion 일정 관리 | OpenAI, Notion |
| [beyondworks-assistant](./beyondworks-assistant/) | 멀티도메인 비즈니스 AI 도우미 | OpenAI, Notion |

## 공통 준비물

모든 스킬을 사용하려면 이것들이 필요해요:

1. **Python 3** (v3.9 이상)
   ```bash
   # 설치 확인
   python3 --version
   ```

2. **pip** (Python 패키지 설치 도구)
   ```bash
   # 설치 확인
   pip3 --version
   ```

3. **API 키** (각 스킬마다 다르니까, 각 스킬 폴더의 가이드를 확인해요)

## 빠른 시작

```bash
# 1. 레포 다운로드
git clone https://github.com/beyondworks/leanskills.git
cd leanskills

# 2. 원하는 스킬 폴더로 이동
cd skills/content-repurposing   # 예: 콘텐츠 재가공

# 3. 해당 스킬의 README.md 또는 SETUP.md를 읽고 따라해요
```

각 스킬의 자세한 설치 방법은 해당 폴더의 가이드를 확인해주세요.
