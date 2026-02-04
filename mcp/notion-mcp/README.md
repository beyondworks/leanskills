# Notion MCP 설치 가이드

Notion MCP는 AI 도우미(Claude, Cursor 등)가 여러분의 Notion 페이지를 읽고, 만들고, 수정할 수 있게 해주는 도구예요.

## 이게 뭔가요?

Notion이라는 메모/문서 앱이 있죠? 이 MCP를 설치하면 AI가 Notion을 직접 조작할 수 있어요.
예를 들어 "내 일정 보여줘", "회의록 페이지 만들어줘" 같은 말을 하면 AI가 알아서 해줍니다.

## 준비물

1. **Node.js** (v18 이상)
   - [https://nodejs.org](https://nodejs.org) 에서 다운로드
   - 설치 후 터미널에서 확인: `node --version`

2. **Notion 계정**
   - [https://www.notion.so](https://www.notion.so) 에서 무료 가입

3. **Notion API 키 (Integration Token)**
   - 아래 "Notion API 키 발급 방법"을 따라 해주세요

## 설치 방법

별도로 설치할 건 없어요! `npx`로 자동 실행됩니다.

## Notion API 키 발급 방법

이 부분이 가장 중요해요. 천천히 따라 해 보세요:

### 1단계: Integration 만들기

1. [https://www.notion.so/my-integrations](https://www.notion.so/my-integrations) 에 접속해요
2. **새 통합(New integration)** 버튼을 클릭해요
3. 이름을 정해요 (예: "내 AI 도우미")
4. 연결할 워크스페이스를 선택해요
5. **제출(Submit)** 클릭
6. 나타나는 **시크릿 키(Internal Integration Secret)** 를 복사해요
   - `ntn_` 으로 시작하는 긴 글자예요

### 2단계: Notion 페이지에 연결하기

AI가 접근할 수 있도록 Notion 페이지에 권한을 줘야 해요:

1. AI가 읽을 Notion 페이지를 열어요
2. 오른쪽 위 **···** (점 세 개) 클릭
3. **연결(Connections)** 클릭
4. 방금 만든 통합(Integration)을 찾아서 추가해요

> **중요**: 이 단계를 빼먹으면 AI가 페이지를 못 읽어요!

## Claude Desktop에 연결하기

### 설정 파일 위치

- **Mac**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

### 설정 내용

```json
{
  "mcpServers": {
    "notion-mcp": {
      "command": "npx",
      "args": ["-y", "@notionhq/notion-mcp-server"],
      "env": {
        "OPENAPI_MCP_HEADERS": "{\"Authorization\": \"Bearer 여기에_Notion_API_키를_넣으세요\", \"Notion-Version\": \"2022-06-28\"}"
      }
    }
  }
}
```

> `OPENAPI_MCP_HEADERS` 값은 반드시 한 줄로 써야 해요. 줄바꿈하면 안 돼요!

## Cursor에서 사용하기

`.cursor/mcp.json` 파일을 만들어요:

```json
{
  "mcpServers": {
    "notion-mcp": {
      "command": "npx",
      "args": ["-y", "@notionhq/notion-mcp-server"],
      "env": {
        "OPENAPI_MCP_HEADERS": "{\"Authorization\": \"Bearer 여기에_Notion_API_키를_넣으세요\", \"Notion-Version\": \"2022-06-28\"}"
      }
    }
  }
}
```

## Claude Code (CLI)에서 사용하기

`~/.claude/settings.json`에 추가해요:

```json
{
  "mcpServers": {
    "notion-mcp": {
      "command": "npx",
      "args": ["-y", "@notionhq/notion-mcp-server"],
      "env": {
        "OPENAPI_MCP_HEADERS": "{\"Authorization\": \"Bearer 여기에_Notion_API_키를_넣으세요\", \"Notion-Version\": \"2022-06-28\"}"
      }
    }
  }
}
```

## 잘 되는지 확인하기

설정을 마치고 Claude Desktop을 다시 시작하면, Claude에게 이렇게 물어봐요:

- "내 Notion 페이지 목록 보여줘"
- "Notion에서 '회의록' 검색해줘"
- "새 Notion 페이지 만들어줘"

AI가 Notion 정보를 알려주면 성공이에요!

## 문제가 생겼을 때

| 문제 | 해결 방법 |
|------|-----------|
| "unauthorized" 오류 | Notion API 키가 맞는지 확인해요 |
| 페이지가 안 보여요 | Notion 페이지에 Integration 연결을 했는지 확인해요 (2단계) |
| npx 실행이 안 돼요 | Node.js가 설치되어 있는지 확인해요: `node --version` |
| JSON 오류 | `OPENAPI_MCP_HEADERS` 값이 한 줄인지 확인해요 |

## 참고 링크

- Notion MCP 공식: [@notionhq/notion-mcp-server](https://www.npmjs.com/package/@notionhq/notion-mcp-server)
- Notion API 문서: [https://developers.notion.com](https://developers.notion.com)
- Notion Integration 설정: [https://www.notion.so/my-integrations](https://www.notion.so/my-integrations)
