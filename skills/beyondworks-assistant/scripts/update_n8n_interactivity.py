#!/usr/bin/env python3
"""
Update n8n workflow to support Slack interactivity (Block Kit buttons).

Fetches the existing workflow (gdxmyb96umqRkEF6) via the n8n REST API,
modifies the node graph to add interactive message handling, and PUTs
the updated workflow back.

Changes applied:
  1. Modify SSH node command to pass user_id and channel_id
  2. Replace response parser with interactive-aware version
  3. Update Slack send node to support Block Kit blocks
  4. Add Webhook node for Slack interactivity endpoint
  5. Add Code node to parse interactive payloads
  6. Add SSH node for resolve_action
  7. Add Code node to parse resolve_action output
  8. Add HTTP Request node to respond via response_url
  9. Wire all new connections

Requirements:
  - N8N_API_KEY environment variable must be set
  - Script must be run on the same host as the n8n instance (localhost:5678)

Usage:
  export N8N_API_KEY="your-api-key"
  python3 update_n8n_interactivity.py [--dry-run]
"""

import json
import os
import sys
import copy
import urllib.request
import urllib.error

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

N8N_BASE_URL = os.environ.get("N8N_BASE_URL", "http://localhost:5678")
N8N_API_KEY = os.environ.get("N8N_API_KEY", "")
WORKFLOW_ID = "gdxmyb96umqRkEF6"

SSH_CREDENTIAL_ID = "0oLkHTGQ5CFQzUHY"

# Node names in the existing workflow (Korean labels)
EXISTING_SSH_NODE = "SSH"  # May also be named differently; we search by type
EXISTING_PARSER_NODE = "응답파싱"
EXISTING_SLACK_SEND_NODE = "Slack전송"

DRY_RUN = "--dry-run" in sys.argv


# ---------------------------------------------------------------------------
# HTTP helpers (stdlib only)
# ---------------------------------------------------------------------------

def api_request(method, path, body=None):
    """Send a request to the n8n API and return parsed JSON."""
    url = f"{N8N_BASE_URL}/api/v1{path}"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-N8N-API-KEY": N8N_API_KEY,
    }

    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")

    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        print(f"[ERROR] HTTP {exc.code} from {method} {url}")
        print(f"        {error_body[:500]}")
        sys.exit(1)
    except urllib.error.URLError as exc:
        print(f"[ERROR] Cannot reach n8n at {url}: {exc.reason}")
        sys.exit(1)


def get_workflow():
    """Fetch the workflow JSON."""
    return api_request("GET", f"/workflows/{WORKFLOW_ID}")


def put_workflow(workflow):
    """Update the workflow via PUT."""
    return api_request("PUT", f"/workflows/{WORKFLOW_ID}", workflow)


# ---------------------------------------------------------------------------
# Node finders
# ---------------------------------------------------------------------------

def find_node(nodes, name=None, node_type=None):
    """Find a node by name or type. Returns (index, node) or (None, None)."""
    for i, node in enumerate(nodes):
        if name and node.get("name") == name:
            return i, node
        if node_type and node.get("type") == node_type and not name:
            return i, node
    return None, None


def find_node_by_name(nodes, name):
    """Find a node by exact name. Returns (index, node) or (None, None)."""
    return find_node(nodes, name=name)


def find_ssh_nodes(nodes):
    """Find all SSH/Command nodes in the workflow."""
    results = []
    for i, node in enumerate(nodes):
        ntype = node.get("type", "")
        if "ssh" in ntype.lower() or "command" in ntype.lower():
            results.append((i, node))
    return results


def max_y_position(nodes):
    """Get the maximum Y position across all nodes."""
    return max((n.get("position", [0, 0])[1] for n in nodes), default=300)


def next_node_id(nodes):
    """Generate a unique node ID that does not collide with existing ones."""
    existing = {n.get("id", "") for n in nodes}
    import hashlib
    import time
    for i in range(100):
        candidate = hashlib.md5(f"interactivity-{i}-{time.time()}".encode()).hexdigest()[:20]
        if candidate not in existing:
            return candidate
    return "new_node_fallback"


# ---------------------------------------------------------------------------
# Node definitions for the interactivity branch
# ---------------------------------------------------------------------------

def make_interactivity_webhook_node(x, y):
    """Webhook node that receives Slack interactive payloads."""
    return {
        "parameters": {
            "httpMethod": "POST",
            "path": "slack-interactivity",
            "responseMode": "responseNode",
            "options": {
                "rawBody": True,
            },
        },
        "name": "Webhook-Interactivity",
        "type": "n8n-nodes-base.webhook",
        "typeVersion": 2,
        "position": [x, y],
        "webhookId": "slack-interactivity",
    }


INTERACTIVITY_PARSER_CODE = r"""
// Parse Slack interactive payload (form-encoded: payload=JSON_STRING)
const rawBody = $input.first().json.body;
let payload;

if (typeof rawBody === 'string') {
  try {
    const decoded = decodeURIComponent(rawBody.replace('payload=', ''));
    payload = JSON.parse(decoded);
  } catch(e) {
    payload = {};
  }
} else if (rawBody && rawBody.payload) {
  payload = typeof rawBody.payload === 'string'
    ? JSON.parse(rawBody.payload)
    : rawBody.payload;
} else {
  payload = rawBody || {};
}

const action = (payload.actions && payload.actions[0]) || {};
const user = (payload.user && payload.user.id) || '';
const channel = (payload.channel && payload.channel.id) || '';
const value = action.value || '';
const responseUrl = payload.response_url || '';

return [{
  json: { value, user, channel, responseUrl }
}];
""".strip()


def make_interactivity_parser_node(x, y):
    """Code node that parses the interactive payload."""
    return {
        "parameters": {
            "jsCode": INTERACTIVITY_PARSER_CODE,
        },
        "name": "InteractivePayload파싱",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [x, y],
    }


def make_resolve_action_ssh_node(x, y):
    """SSH node that calls assistant.py resolve_action."""
    return {
        "parameters": {
            "command": (
                'python3 /root/.claude/skills/beyondworks-assistant/assistant.py'
                ' resolve_action "{{$json.value}}" chat "{{$json.user}}" "{{$json.channel}}"'
            ),
        },
        "name": "SSH-ResolveAction",
        "type": "n8n-nodes-base.ssh",
        "typeVersion": 1,
        "position": [x, y],
        "credentials": {
            "sshPassword": {
                "id": SSH_CREDENTIAL_ID,
                "name": "SSH account",
            },
        },
    }


RESOLVE_RESPONSE_PARSER_CODE = r"""
// Parse resolve_action SSH output
const output = $input.first().json;
const rawOutput = output.stdout || output.data || '';

let parsed;
try {
  parsed = JSON.parse(rawOutput.trim());
} catch(e) {
  parsed = { response: rawOutput.trim() || '처리 중 오류가 발생했습니다.' };
}

const response = parsed.response || '처리 완료';
const domain = parsed.domain || '';

const domainEmoji = {
  schedule: '\ud83d\udcc5', content: '\ud83d\udcda', finance: '\ud83d\udcb0',
  travel: '\u2708\ufe0f', tools: '\ud83d\udd27', business: '\ud83d\udcbc'
};
const prefix = domainEmoji[domain] || '\ud83e\udd16';

// Pass responseUrl through from previous node
const responseUrl = $('InteractivePayload파싱').first().json.responseUrl || '';

return [{
  json: {
    text: `${prefix} ${response}`,
    responseUrl: responseUrl
  }
}];
""".strip()


def make_resolve_response_parser_node(x, y):
    """Code node that parses the resolve_action SSH output."""
    return {
        "parameters": {
            "jsCode": RESOLVE_RESPONSE_PARSER_CODE,
        },
        "name": "ResolveAction응답파싱",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [x, y],
    }


def make_slack_response_url_node(x, y):
    """HTTP Request node that sends the response via Slack response_url."""
    return {
        "parameters": {
            "method": "POST",
            "url": "={{$json.responseUrl}}",
            "sendBody": True,
            "specifyBody": "json",
            "jsonBody": '={\n  "replace_original": false,\n  "text": "{{ $json.text }}"\n}',
            "options": {},
        },
        "name": "Slack-ResponseURL",
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2,
        "position": [x, y],
    }


def make_interactivity_respond_node(x, y):
    """Respond to Webhook node to return 200 OK immediately."""
    return {
        "parameters": {
            "respondWith": "text",
            "responseBody": "",
            "options": {
                "responseCode": 200,
            },
        },
        "name": "Interactivity응답",
        "type": "n8n-nodes-base.respondToWebhook",
        "typeVersion": 1.1,
        "position": [x, y],
    }


# ---------------------------------------------------------------------------
# Updated Code for the existing response parser node
# ---------------------------------------------------------------------------

UPDATED_RESPONSE_PARSER_CODE = r"""
// Parse SSH output with interactive response support
const output = $input.first().json;
const rawOutput = output.stdout || output.data || '';

let parsed;
try {
  parsed = JSON.parse(rawOutput.trim());
} catch(e) {
  parsed = { response: rawOutput.trim() || '처리 중 오류가 발생했습니다.' };
}

const response = parsed.response || '처리 완료';
const interactive = parsed.interactive || null;
const domain = parsed.domain || '';

// Domain emoji prefix
const domainEmoji = {
  schedule: '\ud83d\udcc5', content: '\ud83d\udcda', finance: '\ud83d\udcb0',
  travel: '\u2708\ufe0f', tools: '\ud83d\udd27', business: '\ud83d\udcbc'
};
const prefix = domainEmoji[domain] || '\ud83e\udd16';

if (interactive) {
  // Build Block Kit with buttons
  const blocks = [
    {
      type: "section",
      text: { type: "plain_text", text: `${prefix} ${response}` }
    },
    {
      type: "actions",
      elements: interactive.options.slice(0, 5).map((opt, idx) => ({
        type: "button",
        text: { type: "plain_text", text: opt },
        action_id: `${interactive.action_id_prefix}__${idx}`,
        value: opt
      }))
    }
  ];

  return [{
    json: {
      text: `${prefix} ${response}`,
      blocks: JSON.stringify(blocks),
      isInteractive: true,
      channel: $('Webhook').first().json.event?.channel || ''
    }
  }];
}

return [{
  json: {
    text: `${prefix} ${response}`,
    blocks: '',
    isInteractive: false,
    channel: $('Webhook').first().json.event?.channel || ''
  }
}];
""".strip()


# ---------------------------------------------------------------------------
# Main modification logic
# ---------------------------------------------------------------------------

def modify_workflow(wf):
    """Apply all interactivity modifications to the workflow dict in-place."""
    nodes = wf.get("nodes", [])
    connections = wf.get("connections", {})

    # ------------------------------------------------------------------
    # 1. Modify existing SSH node: update command to pass user_id, channel_id
    # ------------------------------------------------------------------
    ssh_modified = False
    for i, node in enumerate(nodes):
        ntype = node.get("type", "")
        if "ssh" not in ntype.lower():
            continue
        cmd = node.get("parameters", {}).get("command", "")
        if "assistant.py" in cmd and "router" in cmd and "resolve_action" not in cmd:
            old_cmd = cmd
            new_cmd = (
                'python3 /root/.claude/skills/beyondworks-assistant/assistant.py'
                ' router "{{$json.event.text || $json.event.message?.text || \'\'}}"'
                ' chat "{{$json.event.user}}" "{{$json.event.channel}}"'
            )
            node["parameters"]["command"] = new_cmd
            ssh_modified = True
            print(f"[OK] Modified SSH node '{node['name']}' command")
            print(f"     Old: {old_cmd[:80]}...")
            print(f"     New: {new_cmd[:80]}...")
            break

    if not ssh_modified:
        print("[WARN] Could not find existing SSH node with assistant.py router command.")
        print("       Will continue with other modifications.")

    # ------------------------------------------------------------------
    # 2. Update response parser code
    # ------------------------------------------------------------------
    parser_idx, parser_node = find_node_by_name(nodes, EXISTING_PARSER_NODE)
    if parser_node is None:
        # Try fuzzy match
        for i, node in enumerate(nodes):
            name = node.get("name", "")
            if "파싱" in name and "응답" in name:
                parser_idx, parser_node = i, node
                break

    if parser_node:
        parser_node["parameters"]["jsCode"] = UPDATED_RESPONSE_PARSER_CODE
        print(f"[OK] Updated response parser node '{parser_node['name']}' with interactive support")
    else:
        print("[WARN] Could not find response parser node. Skipping parser update.")

    # ------------------------------------------------------------------
    # 3. Update Slack send node to handle blocks
    # ------------------------------------------------------------------
    slack_idx, slack_node = find_node_by_name(nodes, EXISTING_SLACK_SEND_NODE)
    if slack_node is None:
        # Try fuzzy match
        for i, node in enumerate(nodes):
            name = node.get("name", "")
            ntype = node.get("type", "")
            if ("slack" in name.lower() or "slack" in ntype.lower()) and "send" in name.lower():
                slack_idx, slack_node = i, node
                break
            if "전송" in name and ("slack" in name.lower() or "Slack" in name):
                slack_idx, slack_node = i, node
                break

    if slack_node:
        params = slack_node.get("parameters", {})
        # Check if it uses the Slack node or HTTP Request
        ntype = slack_node.get("type", "")
        if "slack" in ntype.lower():
            # n8n Slack node: add blocksUi or otherOptions for blocks
            # The safest approach: add blocks via "Other Options" > "Blocks"
            other_opts = params.get("otherOptions", {})
            other_opts["blocksUi"] = {
                "blocksValues": [
                    {
                        "blockType": "rawJson",
                        "rawJson": "={{$json.blocks || '[]'}}",
                    }
                ]
            }
            params["otherOptions"] = other_opts
            # Also ensure text field references the expression
            params["text"] = "={{$json.text}}"
            print(f"[OK] Updated Slack node '{slack_node['name']}' to support blocks")
        elif "httpRequest" in ntype.lower():
            # If Slack is sent via HTTP Request, update the JSON body
            params["jsonBody"] = (
                '={\n'
                '  "channel": "{{ $json.channel }}",\n'
                '  "text": "{{ $json.text }}",\n'
                '  {{#if $json.isInteractive}}"blocks": {{ $json.blocks }},{{/if}}\n'
                '  "unfurl_links": false\n'
                '}'
            )
            print(f"[OK] Updated HTTP Slack node '{slack_node['name']}' body for blocks")
        else:
            print(f"[WARN] Slack node type '{ntype}' not recognized. Manual update may be needed.")
    else:
        print("[WARN] Could not find Slack send node. Skipping Slack node update.")

    # ------------------------------------------------------------------
    # 4. Add new nodes for the interactivity branch
    # ------------------------------------------------------------------
    # Position the new branch below the existing workflow
    base_y = max_y_position(nodes) + 250
    base_x = 0  # Align with leftmost node

    # Detect existing X positions for alignment
    x_positions = sorted(set(n.get("position", [0, 0])[0] for n in nodes))
    x_start = x_positions[0] if x_positions else 0

    new_nodes = []

    # Node 1: Webhook for interactivity
    webhook_node = make_interactivity_webhook_node(x_start, base_y)
    webhook_node["id"] = next_node_id(nodes + new_nodes)
    new_nodes.append(webhook_node)
    print(f"[OK] Added node: '{webhook_node['name']}' at ({x_start}, {base_y})")

    # Node 2: Parse interactive payload
    parser_x = x_start + 300
    interact_parser_node = make_interactivity_parser_node(parser_x, base_y)
    interact_parser_node["id"] = next_node_id(nodes + new_nodes)
    new_nodes.append(interact_parser_node)
    print(f"[OK] Added node: '{interact_parser_node['name']}' at ({parser_x}, {base_y})")

    # Node 3: SSH resolve_action
    ssh_x = x_start + 600
    resolve_ssh_node = make_resolve_action_ssh_node(ssh_x, base_y)
    resolve_ssh_node["id"] = next_node_id(nodes + new_nodes)
    new_nodes.append(resolve_ssh_node)
    print(f"[OK] Added node: '{resolve_ssh_node['name']}' at ({ssh_x}, {base_y})")

    # Node 4: Parse resolve_action response
    resolve_parser_x = x_start + 900
    resolve_parser_node = make_resolve_response_parser_node(resolve_parser_x, base_y)
    resolve_parser_node["id"] = next_node_id(nodes + new_nodes)
    new_nodes.append(resolve_parser_node)
    print(f"[OK] Added node: '{resolve_parser_node['name']}' at ({resolve_parser_x}, {base_y})")

    # Node 5: HTTP Request to Slack response_url
    slack_resp_x = x_start + 1200
    slack_resp_node = make_slack_response_url_node(slack_resp_x, base_y)
    slack_resp_node["id"] = next_node_id(nodes + new_nodes)
    new_nodes.append(slack_resp_node)
    print(f"[OK] Added node: '{slack_resp_node['name']}' at ({slack_resp_x}, {base_y})")

    # Node 6: Respond to Webhook (return 200 OK to Slack within 3s)
    respond_x = x_start + 300
    respond_y = base_y + 150
    respond_node = make_interactivity_respond_node(respond_x, respond_y)
    respond_node["id"] = next_node_id(nodes + new_nodes)
    new_nodes.append(respond_node)
    print(f"[OK] Added node: '{respond_node['name']}' at ({respond_x}, {respond_y})")

    # Add all new nodes to the workflow
    nodes.extend(new_nodes)

    # ------------------------------------------------------------------
    # 5. Wire connections for the new interactivity branch
    # ------------------------------------------------------------------
    # Connection format: connections[sourceNodeName][outputIndex][connectionType]
    # Each entry is { "node": targetName, "type": "main", "index": inputIndex }

    def add_connection(src_name, dst_name, src_output=0, dst_input=0):
        """Add a connection from src to dst."""
        if src_name not in connections:
            connections[src_name] = {}
        output_key = str(src_output) if isinstance(src_output, int) else src_output
        # n8n uses numeric keys for outputs but in the JSON they are stored
        # under the "main" key as an array of arrays
        if "main" not in connections[src_name]:
            connections[src_name]["main"] = []
        # Ensure the output array is long enough
        while len(connections[src_name]["main"]) <= src_output:
            connections[src_name]["main"].append([])
        conn_entry = {
            "node": dst_name,
            "type": "main",
            "index": dst_input,
        }
        # Avoid duplicates
        if conn_entry not in connections[src_name]["main"][src_output]:
            connections[src_name]["main"][src_output].append(conn_entry)

    # Interactivity branch:
    # Webhook-Interactivity -> InteractivePayload파싱 -> SSH-ResolveAction
    #   -> ResolveAction응답파싱 -> Slack-ResponseURL
    # Webhook-Interactivity -> Interactivity응답 (parallel, immediate 200)
    add_connection("Webhook-Interactivity", "InteractivePayload파싱")
    add_connection("InteractivePayload파싱", "SSH-ResolveAction")
    add_connection("SSH-ResolveAction", "ResolveAction응답파싱")
    add_connection("ResolveAction응답파싱", "Slack-ResponseURL")
    add_connection("Webhook-Interactivity", "Interactivity응답")

    print(f"[OK] Wired {5} new connections for interactivity branch")

    wf["nodes"] = nodes
    wf["connections"] = connections
    return wf


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_workflow(wf):
    """Run basic sanity checks on the modified workflow."""
    nodes = wf.get("nodes", [])
    connections = wf.get("connections", {})
    node_names = {n["name"] for n in nodes}

    errors = []

    # Check required new nodes exist
    required = [
        "Webhook-Interactivity",
        "InteractivePayload파싱",
        "SSH-ResolveAction",
        "ResolveAction응답파싱",
        "Slack-ResponseURL",
        "Interactivity응답",
    ]
    for name in required:
        if name not in node_names:
            errors.append(f"Missing required node: {name}")

    # Check connections reference valid nodes
    for src, outputs in connections.items():
        if src not in node_names:
            errors.append(f"Connection source '{src}' not found in nodes")
        if isinstance(outputs, dict) and "main" in outputs:
            for output_arr in outputs["main"]:
                for conn in output_arr:
                    dst = conn.get("node", "")
                    if dst not in node_names:
                        errors.append(f"Connection target '{dst}' (from '{src}') not found")

    # Check no duplicate node names
    seen = set()
    for n in nodes:
        name = n["name"]
        if name in seen:
            errors.append(f"Duplicate node name: {name}")
        seen.add(name)

    return errors


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    if not N8N_API_KEY:
        print("[ERROR] N8N_API_KEY environment variable is not set.")
        print("        export N8N_API_KEY='your-api-key-here'")
        sys.exit(1)

    print(f"=== n8n Workflow Interactivity Updater ===")
    print(f"    Target: {N8N_BASE_URL}/api/v1/workflows/{WORKFLOW_ID}")
    print(f"    Mode:   {'DRY RUN' if DRY_RUN else 'LIVE'}")
    print()

    # Step 1: Fetch current workflow
    print("[1/4] Fetching current workflow...")
    wf = get_workflow()
    original_node_count = len(wf.get("nodes", []))
    original_conn_count = sum(
        len(arr)
        for outputs in wf.get("connections", {}).values()
        if isinstance(outputs, dict) and "main" in outputs
        for arr in outputs["main"]
    )
    print(f"      Found {original_node_count} nodes, ~{original_conn_count} connections")
    print(f"      Workflow name: {wf.get('name', 'unknown')}")
    print()

    # Step 2: Make a backup copy
    backup = copy.deepcopy(wf)

    # Step 3: Apply modifications
    print("[2/4] Applying modifications...")
    wf = modify_workflow(wf)
    new_node_count = len(wf.get("nodes", []))
    print(f"      Nodes: {original_node_count} -> {new_node_count} (+{new_node_count - original_node_count})")
    print()

    # Step 4: Validate
    print("[3/4] Validating modified workflow...")
    errors = validate_workflow(wf)
    if errors:
        print("      VALIDATION ERRORS:")
        for err in errors:
            print(f"        - {err}")
        print()
        print("[ABORT] Fix validation errors before updating.")
        sys.exit(1)
    print("      All checks passed.")
    print()

    # Step 5: Push or show
    if DRY_RUN:
        print("[4/4] DRY RUN - writing modified workflow to stdout...")
        print()
        # Write to a file instead of stdout for readability
        dry_run_path = "/tmp/n8n_workflow_interactivity_preview.json"
        with open(dry_run_path, "w", encoding="utf-8") as f:
            json.dump(wf, f, ensure_ascii=False, indent=2)
        print(f"      Preview saved to: {dry_run_path}")
        print("      Review the file and re-run without --dry-run to apply.")
    else:
        print("[4/4] Updating workflow via API...")
        result = put_workflow(wf)
        print(f"      Workflow updated successfully.")
        updated_at = result.get("updatedAt", "unknown")
        print(f"      Updated at: {updated_at}")

    print()
    print("=== Done ===")
    print()
    print("Next steps:")
    print("  1. Open n8n UI and verify the workflow visually")
    print("  2. Configure Slack app Interactivity Request URL:")
    print(f"     https://n8n.beyondworks.io/webhook/slack-interactivity")
    print("  3. Test with a message that triggers interactive options")
    print("  4. Verify button clicks route through the resolve_action branch")


if __name__ == "__main__":
    main()
