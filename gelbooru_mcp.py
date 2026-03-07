#!/usr/bin/env python3
"""
Gelbooru MCP Server
Wraps the Gelbooru API (https://gelbooru.com/index.php?page=wiki&s=view&id=18780)
"""

import asyncio
import json
import os
import time
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode
from urllib.request import urlopen, Request
from urllib.error import URLError

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
except ImportError:
    raise SystemExit(
        "mcp package not found. Install it with: pip install mcp"
    )

BASE_URL = "https://gelbooru.com/index.php"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_auth(params: dict) -> dict:
    """Inject API credentials from environment variables if present."""
    api_key = os.getenv("GELBOORU_API_KEY")
    user_id = os.getenv("GELBOORU_USER_ID")
    if api_key:
        params["api_key"] = api_key
    if user_id:
        params["user_id"] = user_id
    return params


def _get(params: dict) -> Any:
    """Perform a synchronous HTTP GET and return parsed JSON."""
    params = {**params, "json": "1"}   # copy — never mutate the caller's dict
    _build_auth(params)
    url = f"{BASE_URL}?{urlencode(params)}"
    req = Request(url, headers={"User-Agent": "GelbooruMCP/1.0"})
    try:
        with urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8")
    except URLError as exc:
        return {"error": str(exc)}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Some endpoints return XML/empty on error; surface the raw text
        return {"raw": raw}


# ---------------------------------------------------------------------------
# Character tag extraction
# ---------------------------------------------------------------------------

# Tags that describe poses, framing, or meta info rather than the character
_PURGE_TAGS: set = {
    "open_mouth", "blush", "closed_mouth", "full_body", "cowboy_shot",
    "holding", "sitting", "upper_body", "simple_background",
    "looking_at_viewer", "black_background", "smile", "closed_eyes",
    "standing", "absurdres", "white_background",
    "looking_away", "parted_lips", "teeth", "tongue", "sweat",
    "outdoors", "indoors", "solo", "1girl", "1boy", "highres",
    "signature",
}

# Any tag containing one of these substrings is also purged
_PURGE_SUBSTRINGS: tuple = (
    "commentary",   # english_commentary, japanese_commentary, etc.
    "patreon",      # patreon_reward, patreon_username, etc.
    "artist",       # artist_name, original_artist, etc.
)


def _should_purge(tag: str) -> bool:
    """Return True if the tag should be excluded from character analysis."""
    t = tag.lower()
    if t in _PURGE_TAGS:
        return True
    return any(sub in t for sub in _PURGE_SUBSTRINGS)

# Hair-style tags that don't contain the word "hair"
_SPECIAL_HAIR_TAGS: set = {
    "ponytail", "twintails", "braid", "ahoge", "two_side_up",
    "side_ponytail", "pigtails", "drill_hair", "ringlets",
    "low_twintails", "high_ponytail",
}


def _get_top_tags(tag_list: List[str], top_n: int) -> List[Tuple[str, int]]:
    """Return the `top_n` most common tags as (tag, count) tuples."""
    counter = Counter(tag_list)
    return counter.most_common(top_n)


# ---------------------------------------------------------------------------
# Disk cache
# ---------------------------------------------------------------------------

# Cache lives next to this file; override with GELBOORU_CACHE_DIR env var
_CACHE_DIR = Path(os.getenv("GELBOORU_CACHE_DIR", Path(__file__).parent / ".gelbooru_cache"))
_CACHE_TTL_SECONDS = int(os.getenv("GELBOORU_CACHE_TTL", str(60 * 60 * 24)))  # 24 h default


def _cache_path(character_name: str, max_images: int) -> Path:
    safe = character_name.replace("/", "_").replace("\\", "_")
    return _CACHE_DIR / f"{safe}__n{max_images}.json"


def _cache_load(character_name: str, max_images: int) -> Optional[Dict[str, Any]]:
    path = _cache_path(character_name, max_images)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if time.time() - data.get("_cached_at", 0) > _CACHE_TTL_SECONDS:
            return None  # stale
        return data
    except Exception:
        return None


def _cache_save(character_name: str, max_images: int, result: Dict[str, Any]) -> None:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = _cache_path(character_name, max_images)
    payload = {**result, "_cached_at": time.time()}
    try:
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except Exception:
        pass  # cache write failures are non-fatal


# ---------------------------------------------------------------------------
# Character tag extraction  (paginated)
# ---------------------------------------------------------------------------

_PAGE_SIZE = 100   # Gelbooru API hard cap per request


def _fetch_character_tags(character_name: str, max_images: int) -> Dict[str, Any]:
    """
    Fetch up to `max_images` highest-scored general/solo posts across multiple
    API pages, tally all tags, and return them split into eye / hair / other buckets.
    Results are cached to disk for 24 hours (configurable via GELBOORU_CACHE_TTL).
    """
    # --- cache hit? ---
    cached = _cache_load(character_name, max_images)
    if cached:
        result = {k: v for k, v in cached.items() if not k.startswith("_")}
        result["character_tags"]["cache_hit"] = True
        return result

    query = f"{character_name} rating:general solo sort:score"
    all_posts: List[dict] = []
    pid = 0

    while len(all_posts) < max_images:
        batch_limit = min(_PAGE_SIZE, max_images - len(all_posts))
        params = {
            "page": "dapi",
            "s": "post",
            "q": "index",
            "tags": query,
            "limit": batch_limit,
            "pid": pid,
        }
        data = _get(params)

        if "error" in data:
            return {"error": data["error"]}

        batch = data.get("post", [])
        if not batch:
            break  # no more results

        all_posts.extend(batch)
        if len(batch) < batch_limit:
            break  # last page was short — we've exhausted results
        pid += 1

    if not all_posts:
        return {"error": f"No posts found for character '{character_name}'."}

    # Collect every tag from every post
    all_tags: List[str] = []
    for post in all_posts:
        tag_str = post.get("tags", "")
        all_tags.extend(tag_str.split())

    # Remove noise tags
    filtered = [t for t in all_tags if not _should_purge(t)]

    # Top 50 most frequent tags with counts
    top_tags_with_counts = _get_top_tags(filtered, top_n=50)
    total_posts = len(all_posts)

    def _enrich(tag: str, count: int) -> Dict[str, Any]:
        return {
            "tag": tag.replace("_", " "),
            "count": count,
            "frequency": round(count / total_posts, 3),
        }

    enriched = [_enrich(tag, count) for tag, count in top_tags_with_counts]

    eye_tags   = [e for e in enriched if "eye" in e["tag"].lower()]
    hair_tags  = [e for e in enriched
                  if "hair" in e["tag"].lower()
                  or e["tag"].replace(" ", "_").lower() in _SPECIAL_HAIR_TAGS]
    other_tags = [e for e in enriched if e not in eye_tags and e not in hair_tags]

    result = {
        "character_tags": {
            "name": character_name,
            "posts_analysed": total_posts,
            "cache_hit": False,
            "eye":   sorted(eye_tags,   key=lambda x: -x["count"]),
            "hair":  sorted(hair_tags,  key=lambda x: -x["count"]),
            "other": sorted(other_tags, key=lambda x: -x["count"]),
        }
    }

    _cache_save(character_name, max_images, result)
    return result


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

def _build_prompt(character_name: str, max_images: int, include_other: bool) -> Dict[str, Any]:
    """
    Calls _fetch_character_tags and assembles a ready-to-use image-gen prompt string.
    Tags are ordered: character name → eye → hair → other (highest frequency first).
    """
    tags_result = _fetch_character_tags(character_name, max_images)
    if "error" in tags_result:
        return tags_result

    ct = tags_result["character_tags"]

    # Human-readable character name: strip _(series) suffix for the label
    display_name = character_name.replace("_", " ")

    parts: List[str] = [display_name]
    parts.extend(e["tag"] for e in ct["eye"])
    parts.extend(h["tag"] for h in ct["hair"])
    if include_other:
        parts.extend(o["tag"] for o in ct["other"])

    prompt_string = ", ".join(parts)

    return {
        "prompt": {
            "character": display_name,
            "posts_analysed": ct["posts_analysed"],
            "cache_hit": ct.get("cache_hit", False),
            "prompt_string": prompt_string,
            "tags": {
                "eye":   [e["tag"] for e in ct["eye"]],
                "hair":  [h["tag"] for h in ct["hair"]],
                "other": [o["tag"] for o in ct["other"]] if include_other else [],
            },
        }
    }


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------

server = Server("gelbooru")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="search_posts",
            description=(
                "Search Gelbooru posts by tags, page, limit, or ID. "
                "Supports all Gelbooru tag syntax: AND (tag1 tag2), OR ({t1~t2}), "
                "NOT (-tag), wildcards (*tag / tag*), meta-tags like "
                "rating:safe/questionable/explicit, score:>=N, width:>=N, "
                "user:name, sort:random, sort:score:desc, etc."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "tags": {
                        "type": "string",
                        "description": (
                            "Tag query string. Examples: 'cat_ears blue_eyes', "
                            "'touhou -rating:explicit', 'score:>=50 sort:score:desc'"
                        ),
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of posts to return (default 20, max 100).",
                        "default": 20,
                        "minimum": 1,
                        "maximum": 100,
                    },
                    "pid": {
                        "type": "integer",
                        "description": "Page number (0-indexed).",
                        "default": 0,
                    },
                    "id": {
                        "type": "integer",
                        "description": "Fetch a single post by its Gelbooru ID.",
                    },
                    "cid": {
                        "type": "integer",
                        "description": "Fetch posts by change ID (Unix timestamp).",
                    },
                },
            },
        ),
        Tool(
            name="get_deleted_posts",
            description=(
                "Retrieve deleted posts. Pass last_id to get everything deleted "
                "above that post ID."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "last_id": {
                        "type": "integer",
                        "description": "Return deleted posts whose ID is above this value.",
                    },
                    "limit": {"type": "integer", "default": 20, "minimum": 1, "maximum": 100},
                },
            },
        ),
        Tool(
            name="search_tags",
            description=(
                "Search Gelbooru tags by name, pattern, or ID. "
                "Useful for autocomplete, tag counts, and tag type lookup."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Exact tag name to look up.",
                    },
                    "names": {
                        "type": "string",
                        "description": "Space-separated list of tag names, e.g. 'cat dog fox'.",
                    },
                    "name_pattern": {
                        "type": "string",
                        "description": (
                            "Wildcard tag search using SQL LIKE syntax. "
                            "Use % for multi-char wildcard, _ for single-char. "
                            "Example: '%choolgirl%'"
                        ),
                    },
                    "id": {
                        "type": "integer",
                        "description": "Look up a tag by its database ID.",
                    },
                    "after_id": {
                        "type": "integer",
                        "description": "Return tags whose ID is greater than this value.",
                    },
                    "limit": {"type": "integer", "default": 20, "minimum": 1, "maximum": 100},
                    "order": {
                        "type": "string",
                        "enum": ["ASC", "DESC"],
                        "description": "Sort direction.",
                    },
                    "orderby": {
                        "type": "string",
                        "enum": ["date", "count", "name"],
                        "description": "Field to sort by.",
                    },
                },
            },
        ),
        Tool(
            name="search_users",
            description="Search Gelbooru users by name or name pattern.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Exact username to search for.",
                    },
                    "name_pattern": {
                        "type": "string",
                        "description": "Wildcard username search (SQL LIKE syntax).",
                    },
                    "limit": {"type": "integer", "default": 20, "minimum": 1, "maximum": 100},
                    "pid": {"type": "integer", "default": 0},
                },
            },
        ),
        Tool(
            name="get_comments",
            description="Retrieve comments for a specific Gelbooru post.",
            inputSchema={
                "type": "object",
                "properties": {
                    "post_id": {
                        "type": "integer",
                        "description": "The post ID whose comments you want to retrieve.",
                    },
                },
                "required": ["post_id"],
            },
        ),
        Tool(
            name="get_character_tags",
            description=(
                "Given a character name (e.g. 'misty_(pokemon)'), fetches the top "
                "highest-scored general/solo posts across multiple pages and returns "
                "the most frequently occurring tags split into three semantic buckets: "
                "eye colour/shape, hair colour/style, and other character traits. "
                "Each tag includes a frequency score. Results are cached to disk for 24 hours."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "character_name": {
                        "type": "string",
                        "description": (
                            "The Gelbooru tag for the character, e.g. 'misty_(pokemon)', "
                            "'rem_(re:zero)', 'saber_(fate)'. Use underscores as Gelbooru does."
                        ),
                    },
                    "max_images": {
                        "type": "integer",
                        "description": (
                            "How many top-scored posts to analyse across all pages "
                            "(default 300). More images = slower but more reliable results. "
                            "Fetched in pages of 100."
                        ),
                        "default": 300,
                        "minimum": 10,
                    },
                },
                "required": ["character_name"],
            },
        ),
        Tool(
            name="build_prompt",
            description=(
                "Given a character name, returns a ready-to-use image-generation prompt "
                "string like 'misty (pokemon), green eyes, orange hair, side ponytail, ...'. "
                "Internally calls get_character_tags with caching, then assembles the prompt "
                "with tags ordered by frequency (eye → hair → other)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "character_name": {
                        "type": "string",
                        "description": (
                            "The Gelbooru tag for the character, e.g. 'misty_(pokemon)'. "
                            "Use underscores as Gelbooru does."
                        ),
                    },
                    "max_images": {
                        "type": "integer",
                        "description": "Posts to analyse (default 300). Cached after first fetch.",
                        "default": 300,
                        "minimum": 10,
                    },
                    "include_other": {
                        "type": "boolean",
                        "description": (
                            "Whether to include non-eye/hair tags (clothing, accessories, etc.) "
                            "in the prompt. Default true."
                        ),
                        "default": True,
                    },
                },
                "required": ["character_name"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    loop = asyncio.get_event_loop()

    if name == "search_posts":
        params = {"page": "dapi", "s": "post", "q": "index"}
        if "tags" in arguments:
            params["tags"] = arguments["tags"]
        if "limit" in arguments:
            params["limit"] = arguments["limit"]
        if "pid" in arguments:
            params["pid"] = arguments["pid"]
        if "id" in arguments:
            params["id"] = arguments["id"]
        if "cid" in arguments:
            params["cid"] = arguments["cid"]
        result = await loop.run_in_executor(None, _get, params)

    elif name == "get_deleted_posts":
        params = {"page": "dapi", "s": "post", "q": "index", "deleted": "show"}
        if "last_id" in arguments:
            params["last_id"] = arguments["last_id"]
        if "limit" in arguments:
            params["limit"] = arguments["limit"]
        result = await loop.run_in_executor(None, _get, params)

    elif name == "search_tags":
        params = {"page": "dapi", "s": "tag", "q": "index"}
        for key in ("name", "names", "name_pattern", "id", "after_id", "limit", "order", "orderby"):
            if key in arguments:
                params[key] = arguments[key]
        result = await loop.run_in_executor(None, _get, params)

    elif name == "search_users":
        params = {"page": "dapi", "s": "user", "q": "index"}
        for key in ("name", "name_pattern", "limit", "pid"):
            if key in arguments:
                params[key] = arguments[key]
        result = await loop.run_in_executor(None, _get, params)

    elif name == "get_comments":
        params = {"page": "dapi", "s": "comment", "q": "index", "post_id": arguments["post_id"]}
        result = await loop.run_in_executor(None, _get, params)

    elif name == "get_character_tags":
        character_name = arguments["character_name"]
        max_images = arguments.get("max_images", 300)
        result = await loop.run_in_executor(
            None, _fetch_character_tags, character_name, max_images
        )

    elif name == "build_prompt":
        character_name = arguments["character_name"]
        max_images = arguments.get("max_images", 300)
        include_other = arguments.get("include_other", True)
        result = await loop.run_in_executor(
            None, _build_prompt, character_name, max_images, include_other
        )

    else:
        result = {"error": f"Unknown tool: {name}"}

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
