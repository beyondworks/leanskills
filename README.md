# leanskills

Beyondworks n8n 워크플로우, Claude Code 스킬, 참조 문서를 관리하는 레포지토리.

n8n 인스턴스 소프트웨어는 [beyondworks/n8n](https://github.com/beyondworks/n8n)에서 관리한다.

## 구조

```
leanskills/
├── skills/                    # Claude Code 스킬 (Python)
│   ├── content-repurposing/   # YouTube → Notion 파이프라인
│   ├── schedule-assistant/    # 스케줄 관리 어시스턴트
│   └── beyondworks-assistant/ # 멀티도메인 Notion 어시스턴트
├── workflows/                 # n8n 워크플로우 JSON
│   ├── schedule-assistant/    # 스케줄 어시스턴트 워크플로우
│   ├── beyondworks-assistant/ # Beyondworks 어시스턴트 워크플로우
│   └── scripts/               # 배포 스크립트
└── n8n-reference/             # n8n 노드/워크플로우 참조 문서
```

## 스킬

### content-repurposing
YouTube 영상 트랜스크립트를 추출하여 블로그 포스트로 변환하고 Notion에 저장.

```bash
cd skills/content-repurposing
pip install -r requirements.txt
APIFY_API_TOKEN=xxx OPENAI_API_KEY=xxx python3 src/repurpose.py "https://youtube.com/watch?v=VIDEO_ID"
```

### schedule-assistant
Notion + Slack 기반 스케줄 관리 어시스턴트.

```bash
cd skills/schedule-assistant
cp .env.example .env  # API 키 설정
python3 run.py
```

### beyondworks-assistant
비즈니스, 콘텐츠, 재무, 일정, 여행 등 멀티도메인 Notion 어시스턴트.

```bash
cd skills/beyondworks-assistant
cp .env.example .env  # API 키 설정
python3 assistant.py
```

## 워크플로우 배포

```bash
cd workflows/scripts
./deploy.sh                          # API 기반 워크플로우 배포
python3 deploy_schedule_assistant.py  # 스케줄 어시스턴트 자동 배포
```
