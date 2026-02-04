import sys
import os
import json
import subprocess
from fetch_metadata import fetch_metadata
from slack_notifier import send_slack_notification

def run_pipeline(video_url):
    print(f"🚀 Starting Repurposing Pipeline for: {video_url}")

    # 0. Check Config
    if not os.path.exists("notion_config.json"):
        print("Error: notion_config.json not found. Run 'python3 src/setup_notion.py' first.")
        sys.exit(1)

    with open("notion_config.json") as f:
        config = json.load(f)

    # API Key from Env
    if "NOTION_API_KEY" not in os.environ:
         print("Warning: NOTION_API_KEY not in env, checking config...")
         if "api_key" in config:
             os.environ["NOTION_API_KEY"] = config["api_key"]
         else:
             print("Error: NOTION_API_KEY not found.")
             sys.exit(1)

    # 1. Fetch Metadata
    print("\n1️⃣  Fetching Metadata...")
    metadata = fetch_metadata(video_url)
    if not metadata:
        sys.exit(1)
    print(f"   - Title: {metadata['title']}")
    print(f"   - Channel: {metadata['channel']}")

    # Save Metadata for next steps
    with open("metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    # 2. Fetch Transcript
    print("\n2️⃣  Fetching Transcript...")
    # executing script as subprocess to reuse existing logic
    subprocess.run([sys.executable, "src/fetch_transcript.py", video_url], check=True)

    # 3. Generate Content & Classify
    print("\n3️⃣  Generating AI Content & Classifying...")
    # We need a new version of blog_gen that outputs JSON including category
    subprocess.run([sys.executable, "src/generate_content.py"], check=True)

    # 4. Save to Notion
    print("\n4️⃣  Saving to Notion...")
    subprocess.run([sys.executable, "src/save_to_notion.py"], check=True)

    # 5. Slack Notification (#insights)
    print("\n5️⃣  Sending Slack Notification...")

    title = ""
    category = ""
    tags = ""
    try:
        with open("content.json") as f:
            c_data = json.load(f)
            meta = c_data.get("meta", {})
            title = meta.get("title") or c_data.get("blog_title") or ""
            category = meta.get("category", "")
            tags_list = meta.get("tags", [])
            if tags_list:
                tags = " ".join(f"#{t}" for t in tags_list[:5])
    except:
        pass

    slack_msg = f"*Content Repurposing Complete*\n"
    if title:
        slack_msg += f"*{title}*\n"
    if category:
        slack_msg += f"Category: {category}\n"
    slack_msg += f"Video: {video_url}\n"
    if tags:
        slack_msg += f"{tags}\n"
    slack_msg += "Notion saved"

    send_slack_notification(slack_msg, "insights")

    print("\n✅ All Done!")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 src/repurpose.py <youtube_url>")
        sys.exit(1)
    run_pipeline(sys.argv[1])
