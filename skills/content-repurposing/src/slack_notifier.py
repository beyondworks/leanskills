import os
import sys
import json
import urllib.request
import urllib.error


def load_config():
    """Load config from notion_config.json"""
    config_path = os.path.join(os.path.dirname(__file__), '..', 'notion_config.json')
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            return json.load(f)
    return {}


def send_slack_notification(message, channel="insights"):
    """
    Send a notification to Slack channel using Bot Token.

    Args:
        message: The message text to send (supports Slack mrkdwn format)
        channel: Slack channel name (without #). Default: 'insights'
    """
    config = load_config()

    # Get Slack Bot Token from config or env
    token = config.get("slack_bot_token") or os.environ.get("SLACK_BOT_TOKEN")

    if not token:
        print("Warning: Slack notification skipped. Missing SLACK_BOT_TOKEN.")
        print("   Set SLACK_BOT_TOKEN env var or add 'slack_bot_token' to notion_config.json")
        return False

    try:
        payload = json.dumps({
            "channel": channel,
            "text": message,
            "unfurl_links": False,
            "unfurl_media": False,
        }).encode('utf-8')

        req = urllib.request.Request(
            "https://slack.com/api/chat.postMessage",
            data=payload,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Authorization": f"Bearer {token}",
            },
        )

        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read().decode('utf-8'))

        if result.get("ok"):
            print(f"Slack #{channel} sent")
            return True
        else:
            print(f"Slack API error: {result.get('error', 'unknown')}")
            return False

    except Exception as e:
        print(f"Slack notification failed: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) >= 2:
        msg = sys.argv[1]
        ch = sys.argv[2] if len(sys.argv) >= 3 else "insights"
        send_slack_notification(msg, ch)
    else:
        send_slack_notification("Content Repurposing test message", "insights")
