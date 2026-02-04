#!/bin/bash
# YouTube Content Repurposing Pipeline Runner
# Usage: ./run_pipeline.sh <youtube_url>

set -e

SKILL_DIR="/Users/yoogeon/.claude/skills/leanskills/content-repurposing"
CONFIG="$SKILL_DIR/notion_config.json"

cd "$SKILL_DIR"

# Load API keys from config
export APIFY_API_TOKEN=$(python3 -c "import json; print(json.load(open('$CONFIG'))['apify_api_key'])")
export NOTION_API_KEY=$(python3 -c "import json; print(json.load(open('$CONFIG'))['notion_api_key'])")
export OPENAI_API_KEY=$(python3 -c "import json; print(json.load(open('$CONFIG'))['openai_api_key'])")

# Run the pipeline
python3 src/repurpose.py "$1"
