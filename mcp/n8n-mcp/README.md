# n8n-MCP 설치 가이드

n8n-MCP는 AI 도우미(Claude, Cursor 등)가 n8n 워크플로우를 이해하고 관리할 수 있게 해주는 도구예요.

## 이게 뭔가요?

n8n이라는 자동화 프로그램이 있는데, 이 MCP를 설치하면 AI가 n8n을 직접 조작할 수 있어요.
예를 들어 "워크플로우 목록 보여줘", "새 워크플로우 만들어줘" 같은 말을 하면 AI가 알아서 해줍니다.

## 준비물

1. **Node.js** (v18 이상)
   - [https://nodejs.org](https://nodejs.org) 에서 다운로드
   - 설치 후 터미널에서 확인: `node --version`

2. **n8n 서버** (이미 실행 중이어야 해요)
   - n8n이 `http://localhost:5678` 에서 돌아가고 있어야 해요
   - n8n API 키가 필요해요 (n8n 설정 > API에서 발급)

## 설치 방법

### 방법 1: npx로 바로 실행 (가장 쉬워요!)

설치할 것 없이 바로 쓸 수 있어요:

```bash
npx n8n-mcp
```

### 방법 2: 직접 설치

```bash
# 1. 소스코드 다운로드
git clone https://github.com/czlonkowski/n8n-mcp.git
cd n8n-mcp

# 2. 필요한 파일 설치
npm install

# 3. 빌드
npm run build

# 4. 실행
npm start
```

## Claude Desktop에 연결하기

Claude Desktop 앱에서 사용하려면 설정 파일을 수정해야 해요.

### 설정 파일 위치

- **Mac**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

### 설정 내용 (문서 조회만)

n8n 노드 정보만 조회하고 싶을 때:

```json
{
  "mcpServers": {
    "n8n-mcp": {
      "command": "npx",
      "args": ["n8n-mcp"],
      "env": {
        "MCP_MODE": "stdio",
        "LOG_LEVEL": "error",
        "DISABLE_CONSOLE_OUTPUT": "true"
      }
    }
  }
}
```

### 설정 내용 (워크플로우 관리 포함)

n8n 워크플로우를 만들고, 수정하고, 실행까지 하고 싶을 때:

```json
{
  "mcpServers": {
    "n8n-mcp": {
      "command": "npx",
      "args": ["n8n-mcp"],
      "env": {
        "MCP_MODE": "stdio",
        "LOG_LEVEL": "error",
        "DISABLE_CONSOLE_OUTPUT": "true",
        "N8N_API_URL": "http://localhost:5678",
        "N8N_API_KEY": "여기에_n8n_API_키를_넣으세요"
      }
    }
  }
}
```

## Cursor에서 사용하기

Cursor 에디터에서 사용하려면 `.cursor/mcp.json` 파일을 만들어요:

```json
{
  "mcpServers": {
    "n8n-mcp": {
      "command": "npx",
      "args": ["n8n-mcp"],
      "env": {
        "MCP_MODE": "stdio",
        "N8N_API_URL": "http://localhost:5678",
        "N8N_API_KEY": "여기에_n8n_API_키를_넣으세요"
      }
    }
  }
}
```

## Claude Code (CLI)에서 사용하기

Claude Code에서 사용하려면 `~/.claude/settings.json`에 추가해요:

```json
{
  "mcpServers": {
    "n8n-mcp": {
      "command": "npx",
      "args": ["n8n-mcp"],
      "env": {
        "MCP_MODE": "stdio",
        "N8N_API_URL": "http://localhost:5678",
        "N8N_API_KEY": "여기에_n8n_API_키를_넣으세요"
      }
    }
  }
}
```

## n8n API 키 발급 방법

1. n8n 웹사이트에 접속해요 (보통 `http://localhost:5678`)
2. 오른쪽 위 **설정(Settings)** 클릭
3. **API** 메뉴 클릭
4. **Create API Key** 버튼 클릭
5. 생성된 키를 복사해서 위 설정에 넣어요

> **주의**: API 키는 비밀번호 같은 거예요! 다른 사람에게 보여주면 안 돼요.

## 잘 되는지 확인하기

설정을 마치고 Claude Desktop을 다시 시작하면, Claude에게 이렇게 물어봐요:

- "n8n에 어떤 워크플로우가 있어?"
- "HTTP Request 노드가 뭐야?"
- "새 워크플로우 만들어줘"

AI가 n8n 정보를 알려주면 성공이에요!

## 문제가 생겼을 때

| 문제 | 해결 방법 |
|------|-----------|
| `npx n8n-mcp` 실행이 안 돼요 | Node.js가 설치되어 있는지 확인해요: `node --version` |
| API 연결이 안 돼요 | n8n 서버가 실행 중인지 확인해요: 브라우저에서 `http://localhost:5678` 접속 |
| API 키 오류가 나요 | n8n 설정에서 API 키를 다시 확인해요 |

## 참고 링크

- n8n-MCP 공식 GitHub: [https://github.com/czlonkowski/n8n-mcp](https://github.com/czlonkowski/n8n-mcp)
- n8n 공식 사이트: [https://n8n.io](https://n8n.io)
