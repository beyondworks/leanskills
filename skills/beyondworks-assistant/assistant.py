#!/usr/bin/env python3
"""
Beyondworks AI Assistant — Unified Router
Usage: python3 assistant.py <domain> "<message>" [mode]
  domain: schedule|content|finance|travel|tools|business|router
  mode: chat|daily_briefing|weekly_briefing|reminder|weekly_digest|monthly_report|weekly_expense|dday_reminder|payment_reminder
"""
import sys
import os
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.config import get_domain_keywords_map
from core.openai_client import classify_domain


def get_handler(domain):
    if domain == "schedule":
        from domains.schedule import handle
    elif domain == "content":
        from domains.content import handle
    elif domain == "finance":
        from domains.finance import handle
    elif domain == "travel":
        from domains.travel import handle
    elif domain == "tools":
        from domains.tools import handle
    elif domain == "business":
        from domains.business import handle
    else:
        return None
    return handle


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: assistant.py <domain> [message] [mode]"}, ensure_ascii=False))
        sys.exit(1)

    domain = sys.argv[1]
    message = sys.argv[2] if len(sys.argv) > 2 else ""
    mode = sys.argv[3] if len(sys.argv) > 3 else "chat"

    # Auto-route if domain is "router"
    if domain == "router":
        if not message:
            print(json.dumps({"error": "router 모드에는 메시지가 필요합니다"}, ensure_ascii=False))
            sys.exit(1)
        keywords_map = get_domain_keywords_map()
        domain = classify_domain(message, keywords_map)

    handler = get_handler(domain)
    if not handler:
        print(json.dumps({"error": f"Unknown domain: {domain}"}, ensure_ascii=False))
        sys.exit(1)

    result = handler(message, mode)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
