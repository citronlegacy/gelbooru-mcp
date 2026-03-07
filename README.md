# gelbooru-mcp

![Python](https://img.shields.io/badge/python-3.10+-blue)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![MCP](https://img.shields.io/badge/MCP-compatible-green)

A Python [MCP](https://modelcontextprotocol.io/) server that wraps the [Gelbooru API](https://gelbooru.com/index.php?page=wiki&s=view&id=18780). Connect it to any MCP-compatible client (Claude Desktop, etc.) to search posts, look up tags, and generate Stable Diffusion prompts from real character appearance data.

---

## Quick Start Examples

**1. Generate a Stable Diffusion prompt for a character**

> "Build me a Stable Diffusion prompt for Rem from Re:Zero."

The LLM calls `build_prompt` with `character_name: "rem_(re:zero)"` and gets back:
```
rem (re:zero), blue eyes, blue hair, short hair, maid, maid headdress, maid apron, ...
```

---

**2. Find high-quality wallpaper images**

> "Show me the top-rated scenery images that are at least 1920px wide."

The LLM calls `search_posts` with `tags: "scenery width:>=1920 sort:score:desc"`.

---

**3. Look up how popular a tag is**

> "How many posts does the tag 'misty_(pokemon)' have on Gelbooru?"

The LLM calls `search_tags` with `name: "misty_(pokemon)"` and reads the `count` field from the response.

---

## Installation

```bash
git clone https://github.com/citronlegacy/gelbooru-mcp.git
cd gelbooru-mcp
chmod +x install.sh && ./install.sh
# or without chmod:
bash install.sh
```

Or manually:

```bash
pip install mcp
```

> **Note:** Add `.gelbooru_cache/` and `.venv/` to your `.gitignore` to avoid accidentally committing cached data or your virtual environment.

---

## Authentication (optional but recommended)

```bash
export GELBOORU_API_KEY="your_api_key"
export GELBOORU_USER_ID="your_user_id"
```

Both values are on your [Gelbooru account options page](https://gelbooru.com/index.php?page=account&s=options). Without them the server still works but requests may be throttled. Patreon supporters of Gelbooru are not rate-limited.

---

## Running the server

```bash
python gelbooru_mcp.py
# or via the venv created by install.sh:
.venv/bin/python gelbooru_mcp.py
```

---

## Claude Desktop config (`claude_desktop_config.json`)

```json
{
  "mcpServers": {
    "gelbooru-mcp": {
      "command": "/absolute/path/to/.venv/bin/python",
      "args": ["/absolute/path/to/gelbooru_mcp.py"],
      "env": {
        "GELBOORU_API_KEY": "your_api_key",
        "GELBOORU_USER_ID": "your_user_id"
      }
    }
  }
}
```

---

## Tools Reference

### `build_prompt`

Fetches the most-tagged `rating:general solo` posts for a character and assembles a ready-to-paste Stable Diffusion prompt string. Internally calls `get_character_tags` so results are cached after the first fetch.

**Parameters**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `character_name` | string | ✅ | — | Gelbooru character tag, e.g. `misty_(pokemon)` |
| `max_images` | integer | ❌ | `300` | Posts to analyse. More = slower first fetch, more reliable tags. Cached afterward. |
| `include_other` | boolean | ❌ | `true` | Include non-eye/hair tags (clothing, accessories, etc.) in the prompt. Set to `false` for appearance-only prompts. |

**Example response**
```json
{
  "prompt": {
    "character": "misty (pokemon)",
    "posts_analysed": 284,
    "cache_hit": false,
    "prompt_string": "misty (pokemon), green eyes, orange hair, side ponytail, gym leader, shorts, suspenders",
    "tags": {
      "eye":   ["green eyes"],
      "hair":  ["orange hair", "side ponytail"],
      "other": ["gym leader", "shorts", "suspenders"]
    }
  }
}
```

**Notes for LLMs:** Always use Gelbooru's underscore format for character names (`misty_(pokemon)` not `Misty (Pokemon)`). If unsure of the exact tag, call `search_tags` with `name_pattern` first to find it.

---

### `get_character_tags`

Same data source as `build_prompt` but returns the full structured tag breakdown with frequency counts instead of a flat prompt string. Use this when you want to inspect, filter, or reformat the tags yourself.

**Parameters**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `character_name` | string | ✅ | — | Gelbooru character tag, e.g. `rem_(re:zero)` |
| `max_images` | integer | ❌ | `300` | Number of top-scored posts to analyse across paginated API requests. |

**Example response**
```json
{
  "character_tags": {
    "name": "rem_(re:zero)",
    "posts_analysed": 300,
    "cache_hit": true,
    "eye": [
      { "tag": "blue eyes", "count": 261, "frequency": 0.87 }
    ],
    "hair": [
      { "tag": "blue hair",  "count": 274, "frequency": 0.913 },
      { "tag": "short hair", "count": 198, "frequency": 0.66  }
    ],
    "other": [
      { "tag": "maid", "count": 231, "frequency": 0.77 }
    ]
  }
}
```

**`frequency`** is the fraction of analysed posts that had that tag (0.0–1.0). Tags near 1.0 are near-universal for the character; tags below 0.3 are situational.

**Cache behaviour:** Results are saved to `.gelbooru_cache/` next to the script and reused for 24 hours. Override with env vars:

| Env var | Default | Description |
|---|---|---|
| `GELBOORU_CACHE_DIR` | `.gelbooru_cache/` next to script | Custom cache folder path |
| `GELBOORU_CACHE_TTL` | `86400` (24 hours) | Cache lifetime in seconds |

---

### `search_posts`

Search Gelbooru posts using any tag combination. Supports the full Gelbooru tag syntax including meta-tags, sorting, and filtering.

**Parameters**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `tags` | string | ❌ | — | Tag query string (see syntax table below) |
| `limit` | integer | ❌ | `20` | Posts to return (max `100`) |
| `pid` | integer | ❌ | `0` | Page number (0-indexed) for pagination |
| `id` | integer | ❌ | — | Fetch a single post by its Gelbooru post ID |
| `cid` | integer | ❌ | — | Fetch posts by change ID (Unix timestamp) |

**Tag syntax**

| Syntax | Meaning |
|---|---|
| `tag1 tag2` | Posts that have both tag1 AND tag2 |
| `{tag1 ~ tag2 ~ tag3}` | Posts that have tag1 OR tag2 OR tag3 |
| `-tag1` | Exclude posts with tag1 |
| `*tag1` | Tags ending with tag1 (wildcard prefix) |
| `tag1*` | Tags starting with tag1 (wildcard suffix) |
| `rating:general` | Filter by rating: `general`, `questionable`, or `explicit` |
| `-rating:explicit` | Exclude a rating |
| `score:>=50` | Score at least 50 |
| `width:>=1920` | Image width ≥ 1920px |
| `height:>1080` | Image height > 1080px |
| `user:bob` | Uploaded by user "bob" |
| `fav:1` | Posts favourited by user with ID 1 |
| `pool:2` | Posts in pool ID 2 |
| `sort:score:desc` | Sort by score (desc or asc) |
| `sort:random` | Random order on every request |
| `sort:random:1234` | Random order with a fixed seed (0–10000) |
| `sort:updated:desc` | Sort by most recently updated |

---

### `get_deleted_posts`

Retrieve posts that have been deleted from Gelbooru, optionally filtered to those above a given post ID.

**Parameters**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `last_id` | integer | ❌ | — | Only return deleted posts whose ID is above this value. Useful for syncing a local mirror. |
| `limit` | integer | ❌ | `20` | Posts to return (max `100`) |

---

### `search_tags`

Look up Gelbooru tags by name, wildcard pattern, or ID. Useful for checking whether a tag exists, finding its post count, discovering related tags, or autocomplete.

**Parameters**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `name` | string | ❌ | — | Exact tag name lookup, e.g. `blue_hair` |
| `names` | string | ❌ | — | Space-separated list of exact tag names, e.g. `cat_ears dog_ears fox_ears` |
| `name_pattern` | string | ❌ | — | SQL LIKE wildcard: `%` matches any number of chars, `_` matches one char. E.g. `%choolgirl%` |
| `id` | integer | ❌ | — | Look up a tag by its database ID |
| `after_id` | integer | ❌ | — | Return tags whose ID is greater than this value |
| `limit` | integer | ❌ | `20` | Tags to return (max `100`) |
| `order` | string | ❌ | — | `ASC` or `DESC` |
| `orderby` | string | ❌ | — | Sort field: `date`, `count`, or `name` |

**Notes for LLMs:** If the user gives a character name in natural language (e.g. "Misty from Pokemon"), use `name_pattern` with `%misty%_(pokemon)%` to find the correct Gelbooru tag before calling `get_character_tags` or `build_prompt`.

---

### `search_users`

Search for Gelbooru user accounts by name.

**Parameters**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `name` | string | ❌ | — | Exact username |
| `name_pattern` | string | ❌ | — | SQL LIKE wildcard username search |
| `limit` | integer | ❌ | `20` | Results to return (max `100`) |
| `pid` | integer | ❌ | `0` | Page number for pagination |

---

### `get_comments`

Retrieve comments on a specific post.

**Parameters**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `post_id` | integer | ✅ | — | The Gelbooru post ID to fetch comments for |

---

## Known Limitations

- **Tag search limit:** Gelbooru enforces a maximum of 2 tags per unauthenticated search query. If you need complex multi-tag queries, set your `GELBOORU_API_KEY` and `GELBOORU_USER_ID`.
- **`get_character_tags` accuracy:** Results depend on how consistently a character is tagged on Gelbooru. Niche or recently added characters may have fewer posts and therefore less reliable frequency data.
- **`rating:general` only for character tools:** `build_prompt` and `get_character_tags` intentionally restrict to `rating:general` to get clean, representative character appearance data. Explicit posts are excluded by design.
- **Cache is per `(character_name, max_images)` pair:** Changing `max_images` busts the cache for that character.

---

## Notes for LLMs

- **Character tag format:** Gelbooru uses `character_(series)` format with underscores. Always convert natural language names before passing to tools — "Rem from Re:Zero" → `rem_(re:zero)`, "Saber from Fate" → `saber_(fate)`.
- **Workflow for character prompts:** If the exact tag is unknown, call `search_tags` with `name_pattern` first → confirm the tag exists and has posts → then call `build_prompt`.
- **Pagination:** `search_posts` returns max 100 results per call. Use `pid` to walk through pages. `get_character_tags` and `build_prompt` handle their own pagination internally.
- **Cache:** `get_character_tags` and `build_prompt` cache results for 24 hours. The `cache_hit` field in the response indicates whether live or cached data was used.
- **Ratings:** Gelbooru uses `general`, `questionable`, and `explicit`. `get_character_tags` and `build_prompt` always filter to `rating:general` for cleaner, more representative character data.

---

## Contributing

Pull requests are welcome. If you find a character tag being miscategorised (e.g. a hair style tag missing from the hair bucket, or a noise tag slipping through the purge filter), please open an issue or PR with the tag and which list it should be added to.

---

## Links

- [Gelbooru API docs](https://gelbooru.com/index.php?page=wiki&s=view&id=18780)
- [Gelbooru tag search cheatsheet](https://gelbooru.com/index.php?page=wiki&s=view&id=26263)
- [MCP documentation](https://modelcontextprotocol.io/)
- [Gelbooru on X/Twitter](https://x.com/gelbooru)
