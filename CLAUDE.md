# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Python MCP server that searches Korean government procurement bids from G2B (나라장터). Integrates with `data.go.kr` public APIs and extracts text from Korean document formats (HWP, HWPX, PDF, DOCX, XLSX).

## Commands

```bash
# Install dependencies
uv sync

# Run server in STDIO mode (for Claude Desktop)
uv run python -m nara_server.server

# Run as named script
uv run nara-server

# Run HTTP mode for Smithery
uv run start

# Test interactively with MCP Inspector (requires Node.js 18+)
npx @modelcontextprotocol/inspector uv --directory . run python -m nara_server.server

# Install dev dependencies
uv sync --extra dev
```

API key must be set before running:
```bash
# Via .env file (recommended for local dev)
echo "NARA_API_KEY=your_key" > .env

# Or environment variable
set NARA_API_KEY=your_key   # Windows
export NARA_API_KEY=your_key  # Linux/Mac
```

## Architecture

### Dual-Transport Design

The server supports two transports, controlled by `@smithery.server(config_schema=ConfigSchema)` in `server.py`:

- **STDIO** (`main()` → `mcp_server.run(transport="stdio")`): Used by Claude Desktop, direct Python invocation. API key comes from `NARA_API_KEY` env var or `.env` file.
- **HTTP** (Smithery deployment, `uv run start`): API key passed via `ctx.session_config.api_key` per-session.

`get_api_key(ctx)` resolves in order: session config → env var → raises `ValueError`.

### Dual-API Search

Every search hits **two separate endpoints** in parallel (sequential in current code):

| Endpoint | Type | Keyword param | Deadline field | Budget field |
|---|---|---|---|---|
| `getBidPblancListInfoServcPPSSrch` | Regular bids (입찰공고) | `bidNtceNm` | `bidClseDt` | `bdgtAmt` / `presmptPrce` |
| `getBfSpecRgstSttusListInfoServcPPSSrch` | Pre-specs (사전규격) | `bfSpecNm` | `opnEndDt` | `asignBdgtAmt` |

Base URL: `http://apis.data.go.kr/1230000/ad/BidPublicInfoService`

Both only search "Service" (용역) type bids — consulting, development, SI projects. Date format is `YYYYMMDDHHMM` as an integer. Search window defaults to 7 days, controlled by `days` parameter passed through from MCP tool → internal function → `get_date_range(days)`. Results auto-filter to only show bids where deadline > now.

The API response nests items at `response.body.items` — the value may be a `list`, `dict` with an `"item"` key (single result), or a string `"null"`. All three cases are handled in both search functions.

### File Extraction Chain (`file_extractor.py`)

`extract_text_from_url(url, filename)` → `extract_text_from_bytes()` (dispatcher) → format-specific extractor.

**HWP extraction has a two-level fallback:**
1. `HWPLoader` from `langchain-teddynote` (primary, handles zlib-compressed HWP)
2. `olefile` direct binary parsing (fallback, reads `PrvText` stream then `BodyText/Section*`)

All library imports use try/except with `HAS_*` flags — missing libraries degrade gracefully rather than crashing.

ZIP files use `select_best_file_from_zip()` to pick one file by priority: filenames containing `제안요청서`/`과업지시서` > `.hwp`/`.hwpx` > `.docx`/`.pdf`.

### MCP Tools

- `get_bids_by_keyword(keyword, days=7)` — 20 results each from both endpoints, returns formatted markdown
- `recommend_bids_for_dept(keyword, department_profile, days=7)` — 30 results each, prepends LLM analysis instructions inline in the returned string
- `analyze_bid_detail(file_url, filename, department_profile?)` — downloads and extracts file text; if `department_profile` provided, prepends strategic analysis prompts

`days` 파라미터는 두 검색 도구에 공통 적용. 기본값 7로 하위 호환성 유지. 특정 공고 분석 시 `days=30~90` 등으로 확장.

### No Test Suite

There is no automated test suite. Use MCP Inspector or Claude Desktop for integration testing.
