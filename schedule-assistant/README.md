# Schedule Assistant Skill

Slack에서 받은 메시지를 기반으로 Notion 일정을 조회하고 AI 응답을 생성하는 스킬입니다.

## 사용법

```bash
# 직접 실행
./run.sh "오늘 할 일이 뭐야?"

# n8n에서 SSH Execute a Command로 호출
/Users/yoogeon/.claude/skills/schedule-assistant/run.sh "사용자 메시지"
```

## 구성 파일

- `run.sh` - 메인 실행 스크립트
- `config.json` - Notion DB ID, API 키 등 설정
- `README.md` - 이 파일

## 환경 변수

- `NOTION_API_KEY` - Notion API 키
- `OPENAI_API_KEY` - OpenAI API 키
