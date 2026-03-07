# Gelbooru MCP Server

A Python [MCP](https://modelcontextprotocol.io/) server that wraps the [Gelbooru API](https://gelbooru.com/index.php?page=wiki&s=view&id=18780). Connect it to any MCP-compatible client (Claude Desktop, etc.) to search posts, look up tags, and generate image-generation prompts for anime characters.

---

## Quick Start Examples

**1. Generate an image prompt for a character**

> "Build me an image generation prompt for Rem from Re:Zero."

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
chmod +x install.sh
./install.sh
```

Or manually:

```bash
pip install mcp
```

## Authentication (optional but recommended)

```bash
export GELBOORU_API_KEY="your_api_key"
export GELBOORU_USER_ID="your_user_id"
```

You can find both values on your Gelbooru account options page. Visit https://gelbooru.com/index.php?page=account&s=options, sign in, and copy the `API key` and your `User ID` into the environment variables shown above. The server will still function without these, but authenticated requests are less likely to be throttled and may have higher rate limits.

If you don't yet have a Gelbooru account, sign up on the site first and then visit the account options page to generate or view your API credentials.

## Running the server

```bash
python gelbooru_mcp.py
# or via the venv created by install.sh:
.venv/bin/python gelbooru_mcp.py
```

---

## Where to find Gelbooru updates

Stay connected with Gelbooru for announcements and site updates. Follow them on X (Twitter): https://x.com/gelbooru


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

Fetches the most-tagged general/solo posts for a character and assembles a ready-to-paste image generation prompt string. Internally calls `get_character_tags` so results are cached after the first fetch.

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

Same data source as `build_prompt` but returns the full structured tag breakdown with frequency counts instead of a prompt string. Use this when you want to inspect or filter the tags yourself rather than getting a pre-built prompt.

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
- `GELBOORU_CACHE_DIR` — custom cache folder path
- `GELBOORU_CACHE_TTL` — TTL in seconds (default `86400`)

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

## Notes for LLMs

- **Character tag format:** Gelbooru uses `character_(series)` format with underscores. Always convert natural language names before passing to tools — "Rem from Re:Zero" → `rem_(re:zero)`, "Saber from Fate" → `saber_(fate)`.
- **Workflow for character prompts:** If the exact tag is unknown, call `search_tags` with `name_pattern` first → confirm the tag exists and has posts → then call `build_prompt`.
- **Pagination:** `search_posts` returns max 100 results per call. Use `pid` to walk through pages. `get_character_tags` and `build_prompt` handle their own pagination internally.
- **Cache:** `get_character_tags` and `build_prompt` cache results for 24 hours. The `cache_hit` field in the response indicates whether live or cached data was used.
- **Ratings:** Gelbooru uses `general`, `questionable`, and `explicit`. `get_character_tags` and `build_prompt` always filter to `rating:general` for cleaner, more representative character data.
