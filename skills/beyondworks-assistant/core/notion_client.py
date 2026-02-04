"""Notion API client for Beyondworks Assistant.

Provides low-level HTTP helpers and higher-level database/page operations
for interacting with the Notion API. Uses only urllib from the standard
library -- no external dependencies.
"""

import json
import urllib.request
import urllib.error

from .config import get_notion_key

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_BASE_URL = "https://api.notion.com/v1"
_NOTION_VERSION = "2022-06-28"
_DEFAULT_TIMEOUT = 30  # seconds


# ---------------------------------------------------------------------------
# Low-level HTTP helper
# ---------------------------------------------------------------------------

def notion_request(method, endpoint, data=None):
    """Execute an authenticated request against the Notion API.

    Args:
        method:   HTTP method (GET, POST, PATCH, DELETE).
        endpoint: API path appended to the base URL, e.g. "databases/{id}/query".
        data:     Optional dict to send as JSON body.

    Returns:
        dict with keys:
            success (bool): True if the request succeeded (2xx).
            data (dict):    Parsed JSON response on success.
            error (str):    Error description on failure.
            status (int):   HTTP status code on failure (when available).
    """
    api_key = get_notion_key()
    if not api_key:
        return {"success": False, "error": "NOTION_API_KEY is not configured"}

    url = f"{_BASE_URL}/{endpoint}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Notion-Version": _NOTION_VERSION,
        "Content-Type": "application/json",
    }

    body = json.dumps(data).encode('utf-8') if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=_DEFAULT_TIMEOUT) as response:
            return {"success": True, "data": json.load(response)}
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode('utf-8') if exc.fp else str(exc)
        return {"success": False, "error": error_body, "status": exc.code}
    except urllib.error.URLError as exc:
        return {"success": False, "error": f"Network error: {exc.reason}"}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# Rich-text helpers
# ---------------------------------------------------------------------------

def parse_rich_text(rich_text_arr):
    """Extract plain text from a Notion rich_text array.

    Args:
        rich_text_arr: List of Notion rich_text objects, each containing
                       a 'plain_text' key.

    Returns:
        Concatenated plain text string, or empty string if input is falsy.
    """
    if not rich_text_arr:
        return ""
    return "".join(item.get('plain_text', '') for item in rich_text_arr)


# ---------------------------------------------------------------------------
# Generic property parser
# ---------------------------------------------------------------------------

def parse_page_properties(page):
    """Parse all properties of a Notion page into a flat dictionary.

    Handles the following Notion property types:
        title, rich_text, number, select, multi_select, date, checkbox,
        url, email, phone_number, relation, formula, rollup, status,
        people, files, created_time, last_edited_time, created_by,
        last_edited_by, unique_id.

    Args:
        page: A Notion page object (dict) as returned by the API.

    Returns:
        dict mapping property names to their extracted Python values.
        Also includes 'id' and 'url' from the page-level metadata.
    """
    result = {
        'id': page.get('id', ''),
        'url': page.get('url', ''),
    }

    props = page.get('properties', {})

    for prop_name, prop_value in props.items():
        prop_type = prop_value.get('type', '')
        result[prop_name] = _extract_property_value(prop_type, prop_value)

    return result


def _extract_property_value(prop_type, prop_value):
    """Extract a Python value from a single Notion property object.

    Args:
        prop_type:  The Notion property type string.
        prop_value: The full property dict from the API.

    Returns:
        Extracted value appropriate for the property type.
    """
    if prop_type == 'title':
        return parse_rich_text(prop_value.get('title', []))

    if prop_type == 'rich_text':
        return parse_rich_text(prop_value.get('rich_text', []))

    if prop_type == 'number':
        return prop_value.get('number')

    if prop_type == 'select':
        select_obj = prop_value.get('select')
        return select_obj.get('name', '') if select_obj else ''

    if prop_type == 'multi_select':
        items = prop_value.get('multi_select', [])
        return [item.get('name', '') for item in items]

    if prop_type == 'date':
        date_obj = prop_value.get('date')
        if not date_obj:
            return {'start': '', 'end': ''}
        return {
            'start': date_obj.get('start', ''),
            'end': date_obj.get('end', ''),
        }

    if prop_type == 'checkbox':
        return prop_value.get('checkbox', False)

    if prop_type == 'url':
        return prop_value.get('url', '')

    if prop_type == 'email':
        return prop_value.get('email', '')

    if prop_type == 'phone_number':
        return prop_value.get('phone_number', '')

    if prop_type == 'relation':
        relations = prop_value.get('relation', [])
        return [rel.get('id', '') for rel in relations]

    if prop_type == 'formula':
        formula_obj = prop_value.get('formula', {})
        formula_type = formula_obj.get('type', '')
        return formula_obj.get(formula_type)

    if prop_type == 'rollup':
        rollup_obj = prop_value.get('rollup', {})
        rollup_type = rollup_obj.get('type', '')
        if rollup_type == 'array':
            return rollup_obj.get('array', [])
        return rollup_obj.get(rollup_type)

    if prop_type == 'status':
        status_obj = prop_value.get('status')
        return status_obj.get('name', '') if status_obj else ''

    if prop_type == 'people':
        people = prop_value.get('people', [])
        return [
            person.get('name', person.get('id', ''))
            for person in people
        ]

    if prop_type == 'files':
        files = prop_value.get('files', [])
        extracted = []
        for file_obj in files:
            file_data = file_obj.get('file') or file_obj.get('external')
            if file_data:
                extracted.append({
                    'name': file_obj.get('name', ''),
                    'url': file_data.get('url', ''),
                })
        return extracted

    if prop_type == 'created_time':
        return prop_value.get('created_time', '')

    if prop_type == 'last_edited_time':
        return prop_value.get('last_edited_time', '')

    if prop_type == 'created_by':
        return prop_value.get('created_by', {}).get('id', '')

    if prop_type == 'last_edited_by':
        return prop_value.get('last_edited_by', {}).get('id', '')

    if prop_type == 'unique_id':
        uid = prop_value.get('unique_id', {})
        prefix = uid.get('prefix', '')
        number = uid.get('number', '')
        return f"{prefix}-{number}" if prefix else str(number)

    # Fallback for unknown property types
    return prop_value.get(prop_type)


# ---------------------------------------------------------------------------
# Database operations
# ---------------------------------------------------------------------------

def query_database(db_id, filter_obj=None, sorts=None, page_size=100):
    """Query a Notion database with optional filter and sort.

    Handles pagination automatically: if there are more results than a
    single page, subsequent requests are made until all results are
    collected or an error occurs.

    Args:
        db_id:      Notion database ID.
        filter_obj: Optional Notion filter object (dict).
        sorts:      Optional list of sort objects.
        page_size:  Number of results per page (max 100).

    Returns:
        dict with keys:
            success (bool): True if all pages were fetched without error.
            results (list): List of page objects.
            error (str):    Error message on failure.
    """
    all_results = []
    start_cursor = None

    while True:
        body = {"page_size": min(page_size, 100)}
        if filter_obj:
            body["filter"] = filter_obj
        if sorts:
            body["sorts"] = sorts
        if start_cursor:
            body["start_cursor"] = start_cursor

        response = notion_request("POST", f"databases/{db_id}/query", body)

        if not response["success"]:
            return {
                "success": False,
                "results": all_results,
                "error": response.get("error", "Unknown error"),
            }

        data = response["data"]
        all_results.extend(data.get("results", []))

        if not data.get("has_more", False):
            break

        start_cursor = data.get("next_cursor")
        if not start_cursor:
            break

    return {"success": True, "results": all_results}


# ---------------------------------------------------------------------------
# Page operations
# ---------------------------------------------------------------------------

def create_page(db_id, properties):
    """Create a new page in a Notion database.

    Args:
        db_id:      Parent database ID.
        properties: Dict of Notion property objects matching the
                    database schema.

    Returns:
        dict from notion_request with success/data/error keys.
    """
    page_data = {
        "parent": {"database_id": db_id},
        "properties": properties,
    }
    return notion_request("POST", "pages", page_data)


def update_page(page_id, properties):
    """Update properties on an existing Notion page.

    Args:
        page_id:    The page ID to update.
        properties: Dict of Notion property objects to set.

    Returns:
        dict from notion_request with success/data/error keys.
    """
    return notion_request("PATCH", f"pages/{page_id}", {"properties": properties})


def archive_page(page_id):
    """Archive (soft-delete) a Notion page.

    Args:
        page_id: The page ID to archive.

    Returns:
        dict from notion_request with success/data/error keys.
    """
    return notion_request("PATCH", f"pages/{page_id}", {"archived": True})
