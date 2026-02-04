# MCP 서버 설정 가이드

MCP(Model Context Protocol)는 AI 도우미가 외부 서비스(n8n, Notion 등)를 사용할 수 있게 해주는 연결 도구예요.

## MCP가 뭔가요?

보통 AI에게 말을 하면, AI는 대답만 해줘요.
하지만 MCP를 연결하면 AI가 직접 프로그램을 조작할 수 있어요!

예를 들어:
- **n8n-MCP** 연결 → AI가 자동화 워크플로우를 만들고 실행할 수 있어요
- **Notion MCP** 연결 → AI가 Notion 문서를 읽고 쓸 수 있어요

## 포함된 MCP 서버

| MCP 서버 | 설명 | 가이드 |
|----------|------|--------|
| [n8n-mcp](./n8n-mcp/) | n8n 워크플로우 자동화 연결 | [설치 가이드](./n8n-mcp/README.md) |
| [notion-mcp](./notion-mcp/) | Notion 문서 읽기/쓰기 연결 | [설치 가이드](./notion-mcp/README.md) |

## 공통 준비물

모든 MCP를 사용하려면 이것들이 필요해요:

1. **Node.js** (v18 이상) - [다운로드](https://nodejs.org)
2. **AI 도구** 중 하나:
   - [Claude Desktop](https://claude.ai/download) (추천!)
   - [Cursor](https://cursor.sh)
   - [Claude Code](https://docs.anthropic.com/en/docs/claude-code)

## 설정 파일을 합치는 방법

여러 MCP를 동시에 사용하고 싶으면, 설정을 하나의 파일에 합쳐야 해요.

### Claude Desktop 예시 (n8n + Notion 동시 사용)

```json
{
  "mcpServers": {
    "n8n-mcp": {
      "command": "npx",
      "args": ["n8n-mcp"],
      "env": {
        "MCP_MODE": "stdio",
        "N8N_API_URL": "http://localhost:5678",
        "N8N_API_KEY": "여기에_n8n_API_키"
      }
    },
    "notion-mcp": {
      "command": "npx",
      "args": ["-y", "@notionhq/notion-mcp-server"],
      "env": {
        "OPENAPI_MCP_HEADERS": "{\"Authorization\": \"Bearer 여기에_Notion_API_키\", \"Notion-Version\": \"2022-06-28\"}"
      }
    }
  }
}
```

각 MCP의 자세한 설정은 해당 폴더의 README를 참고해주세요.
