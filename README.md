# gelbooru-mcp

[![Python](https://img.shields.io/badge/python-3.10+-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP](https://img.shields.io/badge/MCP-compatible-green)](https://modelcontextprotocol.io/)

<a href="https://glama.ai/mcp/servers/citronlegacy/gelbooru-mcp">
  <img width="380" height="200" src="https://glama.ai/mcp/servers/citronlegacy/gelbooru-mcp/badge" alt="Gelbooru MCP server rating" />
</a>


A Python [MCP](https://modelcontextprotocol.io/) server that wraps the [Gelbooru API](https://gelbooru.com/index.php?page=wiki&s=view&id=18780). Connect it to any MCP-compatible client (Claude Desktop, Cursor, etc.) to search posts, look up tags, and generate Stable Diffusion prompts from real character appearance data — all directly from your AI assistant.

---

## ✨ Features

### 🎨 **Stable Diffusion Prompt Generation**
- **Character Prompts**: Auto-generate accurate SD prompts from real Gelbooru tag frequency data
- **Appearance Breakdown**: Separate eye, hair, and clothing/accessory tag categories
- **Smart Caching**: Results cached for 24 hours — no repeated API hits

### 🔍 **Post & Tag Search**
- **Advanced Filtering**: Search by tags, score, resolution, rating, uploader, pool, and more
- **Full Tag Syntax**: AND, OR, wildcard, exclusion, meta-tags, sorting, and pagination
- **Tag Lookup**: Check tag existence, post counts, and discover related tags

### 👥 **Community Tools**
- **User Search**: Find Gelbooru user accounts by name or wildcard pattern
- **Comments**: Retrieve post comments for any post ID
- **Deleted Posts**: Track removed content above a given post ID

---

## 📦 Installation

### Prerequisites
- Python 3.10+
- `git`

### Quick Start

1. **Clone the repository:**
```bash
git clone https://github.com/citronlegacy/gelbooru-mcp.git
cd gelbooru-mcp
```

2. **Run the installer:**
```bash
chmod +x install.sh && ./install.sh
# or without chmod:
bash install.sh
```

3. **Or install manually:**
```bash
pip install mcp
```

> **Note:** Add `.gelbooru_cache/` and `.venv/` to your `.gitignore` to avoid committing cached data or your virtual environment.

### Getting a Gelbooru API Key

1. Visit your [Gelbooru account options page](https://gelbooru.com/index.php?page=account&s=options)
2. Log in to your Gelbooru account
3. Copy your **API Key** and **User ID**
4. Set them as environment variables (see below)

---

## 🔑 Authentication

API credentials are optional but strongly recommended — unauthenticated requests are throttled and limited to 2 tags per query. Gelbooru Patreon supporters receive unlimited requests.

```bash
export GELBOORU_API_KEY="your_api_key"
export GELBOORU_USER_ID="your_user_id"
```

Both values are on your [Gelbooru account options page](https://gelbooru.com/index.php?page=account&s=options). Without them the server still works but requests may be throttled. Patreon supporters of Gelbooru are not rate-limited.

---

## ▶️ Running the Server

```bash
python gelbooru_mcp.py
# or via the venv created by install.sh:
.venv/bin/python gelbooru_mcp.py
```

---

## ⚙️ Configuration

### Claude Desktop

Add the following to your `claude_desktop_config.json`:

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

### Other MCP Clients

Configure according to your client's documentation:
- **Command**: `/absolute/path/to/.venv/bin/python`
- **Args**: `/absolute/path/to/gelbooru_mcp.py`
- **Transport**: stdio

---

## 💡 Usage Examples

**Generate a Stable Diffusion prompt for a character**

> "Build me a Stable Diffusion prompt for Rem from Re:Zero."

The LLM calls `build_prompt` with `character_name: "rem_(re:zero)"` and gets back:
```
rem (re:zero), blue eyes, blue hair, short hair, maid, maid headdress, maid apron, ...
```

---

**Find high-quality wallpaper images**

> "Show me the top-rated scenery images that are at least 1920px wide."

The LLM calls `search_posts` with `tags: "scenery width:>=1920 sort:score:desc"`.

---

**Look up how popular a tag is**

> "How many posts does the tag 'misty_(pokemon)' have on Gelbooru?"

The LLM calls `search_tags` with `name: "misty_(pokemon)"` and reads the `count` field.

---

## 🛠️ Available Tools

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `build_prompt` | Generate a Stable Diffusion prompt string for a character | `character_name`, `max_images`, `include_other` |
| `get_character_tags` | Get structured tag breakdown with frequency counts | `character_name`, `max_images` |
| `search_posts` | Search posts with full tag syntax support | `tags`, `limit`, `pid`, `id` |
| `search_tags` | Look up tags by name, pattern, or ID | `name`, `name_pattern`, `orderby`, `limit` |
| `search_users` | Find Gelbooru user accounts | `name`, `name_pattern`, `limit` |
| `get_comments` | Retrieve comments for a post | `post_id` |
| `get_deleted_posts` | List recently deleted posts | `last_id`, `limit` |

---

## 📖 Tools Reference

### `build_prompt`

Fetches the most-tagged `rating:general solo` posts for a character and assembles a ready-to-paste Stable Diffusion prompt string. Internally calls `get_character_tags` so results are cached after the first fetch.

**Parameters**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `character_name` | string | ✅ | — | Gelbooru character tag, e.g. `misty_(pokemon)` |
| `max_images` | integer | ❌ | `300` | Posts to analyse. More = slower first fetch, more reliable tags. Cached afterward. |
| `include_other` | boolean | ❌ | `true` | Include non-eye/hair tags (clothing, accessories, etc.). Set to `false` for appearance-only prompts. |

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

> **LLM Tip:** Always use Gelbooru's underscore format (`misty_(pokemon)` not `Misty (Pokemon)`). If unsure of the exact tag, call `search_tags` with `name_pattern` first.

---

### `get_character_tags`

Same data source as `build_prompt` but returns the full structured tag breakdown with frequency counts. Use this when you want to inspect, filter, or reformat tags yourself.

**Parameters**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `character_name` | string | ✅ | — | Gelbooru character tag, e.g. `rem_(re:zero)` |
| `max_images` | integer | ❌ | `300` | Number of top-scored posts to analyse. |

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

`frequency` is the fraction of analysed posts that had that tag (0.0–1.0). Tags near 1.0 are near-universal; tags below 0.3 are situational.

**Cache environment variables:**

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
| `tags` | string | ❌ | — | Tag query string (see [Tag Syntax Reference](#️-tag-syntax-reference) below) |
| `limit` | integer | ❌ | `20` | Posts to return (max `100`) |
| `pid` | integer | ❌ | `0` | Page number (0-indexed) for pagination |
| `id` | integer | ❌ | — | Fetch a single post by its Gelbooru post ID |
| `cid` | integer | ❌ | — | Fetch posts by change ID (Unix timestamp) |

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

Look up Gelbooru tags by name, wildcard pattern, or ID. Useful for checking tag existence, finding post counts, discovering related tags, or autocomplete.

**Parameters**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `name` | string | ❌ | — | Exact tag name, e.g. `blue_hair` |
| `names` | string | ❌ | — | Space-separated list of exact tag names, e.g. `cat_ears dog_ears fox_ears` |
| `name_pattern` | string | ❌ | — | SQL LIKE wildcard: `%` = any chars, `_` = one char. E.g. `%schoolgirl%` |
| `id` | integer | ❌ | — | Look up a tag by its database ID |
| `after_id` | integer | ❌ | — | Return tags with ID greater than this value |
| `limit` | integer | ❌ | `20` | Tags to return (max `100`) |
| `order` | string | ❌ | — | `ASC` or `DESC` |
| `orderby` | string | ❌ | — | Sort field: `date`, `count`, or `name` |

> **LLM Tip:** If the user gives a character name in natural language (e.g. "Misty from Pokemon"), use `name_pattern` with `%misty%_(pokemon)%` to find the correct Gelbooru tag before calling `get_character_tags` or `build_prompt`.

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

## 🏷️ Tag Syntax Reference

| Syntax | Meaning |
|---|---|
| `tag1 tag2` | Posts with both tag1 AND tag2 |
| `{tag1 ~ tag2 ~ tag3}` | Posts with tag1 OR tag2 OR tag3 |
| `-tag1` | Exclude posts with tag1 |
| `*tag1` | Wildcard prefix (tags ending with tag1) |
| `tag1*` | Wildcard suffix (tags starting with tag1) |
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

## 🤖 Notes for LLMs

- **Character tag format:** Gelbooru uses `character_(series)` format with underscores. Always convert natural language names before passing to tools — "Rem from Re:Zero" → `rem_(re:zero)`, "Saber from Fate" → `saber_(fate)`.
- **Workflow for character prompts:** If the exact tag is unknown, call `search_tags` with `name_pattern` first → confirm the tag exists and has posts → then call `build_prompt`.
- **Pagination:** `search_posts` returns max 100 results per call. Use `pid` to walk through pages. `get_character_tags` and `build_prompt` handle their own pagination internally.
- **Cache:** `get_character_tags` and `build_prompt` cache results for 24 hours. The `cache_hit` field in the response indicates whether live or cached data was used.
- **Ratings:** Gelbooru uses `general`, `questionable`, and `explicit`. `get_character_tags` and `build_prompt` always filter to `rating:general` for cleaner, more representative character data.

---

## ⚠️ Known Limitations

- **Tag search limit:** Gelbooru enforces a maximum of 2 tags per unauthenticated search query. For complex multi-tag queries, set `GELBOORU_API_KEY` and `GELBOORU_USER_ID`.
- **`get_character_tags` accuracy:** Results depend on how consistently a character is tagged on Gelbooru. Niche or recently added characters may have fewer posts and less reliable frequency data.
- **`rating:general` only for character tools:** `build_prompt` and `get_character_tags` intentionally restrict to `rating:general` for clean, representative appearance data. Explicit posts are excluded by design.
- **Cache is per `(character_name, max_images)` pair:** Changing `max_images` busts the cache for that character.

---

## 🐛 Troubleshooting

**Server won't start:**
- Ensure Python 3.10+ is installed: `python --version`
- Verify the virtual environment was created: `ls .venv/`
- Re-run the installer: `bash install.sh`

**API rate limiting / throttled requests:**
- Set `GELBOORU_API_KEY` and `GELBOORU_USER_ID` environment variables
- Gelbooru Patreon supporters receive unlimited requests

**Character not found / empty results:**
- Confirm the tag exists with `search_tags` using `name_pattern`
- Check spelling — Gelbooru uses `character_(series)` underscore format
- Some characters may have very few consistently tagged posts

**Tag syntax errors / too many tags:**
- Unauthenticated users are limited to 2 tags per query
- Authenticate with API credentials for complex multi-tag searches

---

## 🤝 Contributing

Pull requests are welcome! If you find a character tag being miscategorised (e.g. a hair style tag missing from the hair bucket, or a noise tag slipping through the purge filter), please open an issue or PR with the tag and which list it belongs in.

### Development Setup
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 🔗 Links

- 📚 [Gelbooru API docs](https://gelbooru.com/index.php?page=wiki&s=view&id=18780)
- 🏷️ [Gelbooru tag search cheatsheet](https://gelbooru.com/index.php?page=wiki&s=view&id=26263)
- 🔧 [MCP documentation](https://modelcontextprotocol.io/)
- 🐦 [Gelbooru on X/Twitter](https://x.com/gelbooru)
- 🐛 [Bug Reports](https://github.com/citronlegacy/gelbooru-mcp/issues)
- 💡 [Feature Requests & Discussions](https://github.com/citronlegacy/gelbooru-mcp/discussions)
