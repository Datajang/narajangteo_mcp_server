#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Nara MCP Server - Korean Government Procurement Bid Search
나라장터 입찰공고 검색 MCP 서버
"""

import sys
import os

# Force UTF-8 encoding for Windows
if sys.platform == 'win32':
    # Set environment variables for UTF-8
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    # Reconfigure stdout/stderr to use UTF-8
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')

import asyncio
from datetime import datetime, timedelta
from typing import Any

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from file_extractor import extract_text_from_url

# API Configuration
SERVICE_KEY = os.getenv("NARA_API_KEY")
if not SERVICE_KEY:
    raise ValueError(
        "NARA_API_KEY environment variable is required.\n"
        "Please set your API key in the MCP client configuration.\n"
        "Get your API key from: https://www.data.go.kr/\n"
        "Search for '나라장터 입찰정보' and register for the service."
    )

BASE_URL = "http://apis.data.go.kr/1230000/ad/BidPublicInfoService"
ENDPOINT = "getBidPblancListInfoServcPPSSrch"


def get_date_range_for_last_month() -> tuple[int, int]:
    """
    Get date range for the last 7 days (reduced from 30 to increase open bid rate).
    Returns: (start_date, end_date) in YYYYMMDDHHMM format as integers
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)

    # Format: YYYYMMDDHHMM
    start_dt_int = int(start_date.strftime("%Y%m%d0000"))
    end_dt_int = int(end_date.strftime("%Y%m%d2359"))

    return start_dt_int, end_dt_int


def is_bid_open(close_datetime_str: str) -> bool:
    """
    입찰 마감일시가 현재 시간 이후인지 확인

    Args:
        close_datetime_str: 마감일시 문자열 (YYYYMMDDHHMM 형식)

    Returns:
        True if 마감일이 미래 (진행중), False if 마감됨
    """
    try:
        # Parse: "202501201430" -> datetime object
        close_dt = datetime.strptime(close_datetime_str, "%Y%m%d%H%M")
        now = datetime.now()
        return close_dt > now
    except:
        # 파싱 실패 시 일단 포함 (안전)
        return True


async def search_bids_by_keyword(keyword: str) -> str:
    """
    Search for service-type bid notices using a keyword.

    Args:
        keyword: Search term for bid title (공고명)

    Returns:
        Formatted string with bid information
    """
    # Ensure keyword is properly encoded as UTF-8
    if isinstance(keyword, bytes):
        keyword = keyword.decode('utf-8', errors='replace')
    else:
        # Re-encode to ensure proper UTF-8
        keyword = keyword.encode('utf-8', errors='replace').decode('utf-8')

    start_date, end_date = get_date_range_for_last_month()

    params = {
        "ServiceKey": SERVICE_KEY,
        "type": "json",
        "inqryDiv": "1",  # Posted date
        "inqryBgnDt": start_date,
        "inqryEndDt": end_date,
        "bidNtceNm": keyword,
        "numOfRows": "20",
        "pageNo": "1"
    }

    # Properly encode Korean characters in URL
    url = f"{BASE_URL}/{ENDPOINT}"

    # Debug: Log request details
    import sys
    print(f"🔍 DEBUG - Keyword received: '{keyword}'", file=sys.stderr)
    print(f"🔍 DEBUG - Keyword bytes: {keyword.encode('utf-8')}", file=sys.stderr)
    print(f"🔍 DEBUG - Request URL: {url}", file=sys.stderr)
    print(f"🔍 DEBUG - Params: {params}", file=sys.stderr)

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        # Debug: Log raw response
        print(f"🔍 DEBUG - Response: {data}", file=sys.stderr)

        # Check API response status
        header = data.get("response", {}).get("header", {})
        result_code = header.get("resultCode")
        result_msg = header.get("resultMsg", "")

        if result_code != "00":
            return f"❌ API Error: {result_msg} (Code: {result_code})"

        # Extract items
        body = data.get("response", {}).get("body", {})
        items = body.get("items")

        # Handle different response structures
        if not items:
            return f"📭 No bid notices found for keyword: '{keyword}' in the last 30 days."

        # items can be a list, dict with "item" key, or empty string ""
        if isinstance(items, str):
            return f"📭 No bid notices found for keyword: '{keyword}' in the last 30 days."

        # Case 1: items is already a list of bid objects
        if isinstance(items, list):
            item_list = items
        # Case 2: items is a dict with "item" key
        elif isinstance(items, dict):
            if not items.get("item"):
                return f"📭 No bid notices found for keyword: '{keyword}' in the last 30 days."
            item_list = items.get("item", [])
            # If single item, convert to list
            if isinstance(item_list, dict):
                item_list = [item_list]
        else:
            return f"📭 No bid notices found for keyword: '{keyword}' in the last 30 days."

        if not item_list:
            return f"📭 No bid notices found for keyword: '{keyword}' in the last 30 days."

        # 마감되지 않은 공고만 필터링
        open_bids = [item for item in item_list if is_bid_open(item.get("bidClseDt", ""))]

        if not open_bids:
            return f"📭 No open bid notices found for keyword: '{keyword}' (all bids are closed)"

        # Format results
        total_count = body.get("totalCount", len(item_list))
        results = [f"🔍 Found {total_count} bid notice(s) total, {len(open_bids)} still open for keyword: '{keyword}'\n"]
        # Convert int dates to string and extract YYYYMMDD
        start_date_str = str(start_date)[:8]
        end_date_str = str(end_date)[:8]
        results.append(f"📅 Search period: {start_date_str} ~ {end_date_str}\n")
        results.append("=" * 80 + "\n")

        for idx, item in enumerate(open_bids, 1):
            bid_name = item.get("bidNtceNm", "N/A")
            bid_no = item.get("bidNtceNo", "N/A")
            deadline = item.get("bidClseDt", "N/A")
            spec_url = item.get("ntceSpecDocUrl1", "")
            demand_org = item.get("dminsttNm", "N/A")

            results.append(f"\n## {idx}. {bid_name}\n")
            results.append(f"   📌 공고번호: {bid_no}\n")
            results.append(f"   🏢 수요기관: {demand_org}\n")
            results.append(f"   ⏰ 마감일시: {deadline}\n")

            if spec_url:
                results.append(f"   📎 제안요청서: {spec_url}\n")
            else:
                results.append(f"   📎 제안요청서: 없음\n")

            results.append("\n" + "-" * 80 + "\n")

        return "".join(results)

    except httpx.HTTPError as e:
        return f"❌ HTTP Error: {str(e)}"
    except Exception as e:
        return f"❌ Error: {str(e)}"


async def search_bids_for_dept(keyword: str, department_profile: str) -> str:
    """
    부서 맞춤형 입찰공고 검색 (§7)
    30개 결과를 가져와서 부서 프로필과 함께 반환
    LLM 클라이언트가 Top 5 선정

    Args:
        keyword: 검색 키워드
        department_profile: 부서/팀 설명

    Returns:
        30개 결과 + 부서 프로필 컨텍스트
    """
    if isinstance(keyword, bytes):
        keyword = keyword.decode('utf-8', errors='replace')
    else:
        keyword = keyword.encode('utf-8', errors='replace').decode('utf-8')

    start_date, end_date = get_date_range_for_last_month()

    params = {
        "ServiceKey": SERVICE_KEY,
        "type": "json",
        "inqryDiv": "1",
        "inqryBgnDt": start_date,
        "inqryEndDt": end_date,
        "bidNtceNm": keyword,
        "numOfRows": "30",  # 더 많은 결과 가져오기
        "pageNo": "1"
    }

    url = f"{BASE_URL}/{ENDPOINT}"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        header = data.get("response", {}).get("header", {})
        result_code = header.get("resultCode")
        result_msg = header.get("resultMsg", "")

        if result_code != "00":
            return f"❌ API Error: {result_msg} (Code: {result_code})"

        body = data.get("response", {}).get("body", {})
        items = body.get("items")

        if not items or isinstance(items, str):
            return f"📭 No bid notices found for keyword: '{keyword}'"

        if isinstance(items, list):
            item_list = items
        elif isinstance(items, dict):
            if not items.get("item"):
                return f"📭 No bid notices found for keyword: '{keyword}'"
            item_list = items.get("item", [])
            if isinstance(item_list, dict):
                item_list = [item_list]
        else:
            return f"📭 No bid notices found for keyword: '{keyword}'"

        if not item_list:
            return f"📭 No bid notices found for keyword: '{keyword}'"

        # 마감되지 않은 공고만 필터링
        open_bids = [item for item in item_list if is_bid_open(item.get("bidClseDt", ""))]

        if not open_bids:
            return f"📭 No open bid notices found for keyword: '{keyword}' (all bids are closed)"

        # 부서 프로필 컨텍스트와 함께 결과 포맷팅
        total_count = body.get("totalCount", len(item_list))
        results = [
            f"🎯 Department-Filtered Bid Search Results",
            f"",
            f"📋 **Department Profile:** {department_profile}",
            f"🔍 **Keyword:** {keyword}",
            f"📊 **Total Open Bids:** {len(open_bids)} (out of {total_count} total)",
            f"",
            f"=" * 80,
            f"",
            f"**Instructions for LLM:** Please analyze the following bids and select the TOP 5 most relevant bids for the department profile above. For each selected bid, provide a one-line reason why it fits the department.",
            f"",
            f"=" * 80,
            f""
        ]

        for idx, item in enumerate(open_bids, 1):
            bid_name = item.get("bidNtceNm", "N/A")
            bid_no = item.get("bidNtceNo", "N/A")
            deadline = item.get("bidClseDt", "N/A")
            spec_url = item.get("ntceSpecDocUrl1", "")
            spec_filename = item.get("ntceSpecFileNm1", "")
            demand_org = item.get("dminsttNm", "N/A")
            ntce_org = item.get("ntceInsttNm", "N/A")

            results.append(f"### [{idx}] {bid_name}")
            results.append(f"- 공고번호: {bid_no}")
            results.append(f"- 수요기관: {demand_org}")
            results.append(f"- 공고기관: {ntce_org}")
            results.append(f"- 마감일시: {deadline}")
            if spec_url:
                results.append(f"- 첨부파일: {spec_filename or 'Available'}")
                results.append(f"- 첨부URL: {spec_url}")
            results.append("")

        return "\n".join(results)

    except httpx.HTTPError as e:
        return f"❌ HTTP Error: {str(e)}"
    except Exception as e:
        return f"❌ Error: {str(e)}"


async def analyze_bid_detail(file_url: str, filename: str, department_profile: str = "") -> str:
    """
    입찰공고 첨부파일 다운로드 및 텍스트 추출 (§9)

    Args:
        file_url: 첨부파일 URL (ntceSpecDocUrl1)
        filename: 파일명 (ntceSpecFileNm1)
        department_profile: 부서/팀 설명 (선택)

    Returns:
        추출된 텍스트 + 분석 프롬프트 컨텍스트
    """
    try:
        # 파일 다운로드 및 텍스트 추출
        extracted_text = await extract_text_from_url(file_url, filename)

        # 텍스트 길이 제한 (너무 길면 요약 필요)
        max_chars = 15000
        if len(extracted_text) > max_chars:
            extracted_text = extracted_text[:max_chars] + "\n\n... [Text truncated due to length]"

        # 결과 포맷팅
        results = [
            f"📄 **Bid Document Analysis**",
            f"",
            f"📎 **File:** {filename}",
            f"🔗 **Source:** {file_url}",
        ]

        if department_profile:
            results.extend([
                f"",
                f"📋 **Department Profile:** {department_profile}",
                f"",
                f"=" * 80,
                f"",
                f"**Instructions for Strategic Analysis:**",
                f"Based on the extracted text below, analyze this project from the perspective of '{department_profile}':",
                f"1. **Fit Score (0-100):** How well does this project match the team's skills?",
                f"2. **Core Tasks:** List only tasks that this team would perform",
                f"3. **Winning Strategy:** Suggest 3 specific approaches to appeal to the client",
                f"4. **Risk Factors:** Identify risky clauses (tech stack, timeline, penalties)",
                f"",
                f"=" * 80,
            ])

        results.extend([
            f"",
            f"## Extracted Document Content:",
            f"",
            extracted_text
        ])

        return "\n".join(results)

    except Exception as e:
        return f"❌ Failed to analyze bid document: {str(e)}\n\nManual link: {file_url}"


# Create MCP server instance
app = Server("nara-mcp-server")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools."""
    return [
        Tool(
            name="get_bids_by_keyword",
            description=(
                "Search Korean government procurement bid notices (나라장터 입찰공고) "
                "for the last 30 days using a keyword. Returns service-type (용역) bids "
                "including consulting, development, and SI projects."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": (
                            "Search keyword for bid title (공고명). "
                            "Examples: '인공지능', 'AI', '플랫폼', '시스템 구축', etc."
                        )
                    }
                },
                "required": ["keyword"]
            }
        ),
        Tool(
            name="recommend_bids_for_dept",
            description=(
                "Search bids with department context for personalized recommendations. "
                "Returns up to 30 results with instructions for LLM to filter Top 5 "
                "most relevant bids based on department profile."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "Search keyword (e.g., 'AI', 'Cloud', '플랫폼')"
                    },
                    "department_profile": {
                        "type": "string",
                        "description": (
                            "Description of your team/department. "
                            "Examples: 'UI/UX 디자인팀', 'Database Migration Unit', "
                            "'AI/ML 개발팀', '클라우드 인프라팀'"
                        )
                    }
                },
                "required": ["keyword", "department_profile"]
            }
        ),
        Tool(
            name="analyze_bid_detail",
            description=(
                "Download and extract text from bid attachment (RFP/제안요청서) for "
                "strategic analysis. Supports HWP, HWPX, PDF, DOCX, XLSX, and ZIP files. "
                "ZIP files are processed with priority: 제안요청서 > 과업지시서 > .hwp > .pdf"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "file_url": {
                        "type": "string",
                        "description": "Attachment URL (ntceSpecDocUrl1 from search results)"
                    },
                    "filename": {
                        "type": "string",
                        "description": "Filename (ntceSpecFileNm1 from search results)"
                    },
                    "department_profile": {
                        "type": "string",
                        "description": (
                            "Optional: Your team description for strategic analysis. "
                            "If provided, response includes analysis prompts for Fit Score, "
                            "Core Tasks, Winning Strategy, and Risk Factors."
                        )
                    }
                },
                "required": ["file_url", "filename"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool execution."""
    if name == "get_bids_by_keyword":
        keyword = arguments.get("keyword")
        if not keyword:
            return [TextContent(type="text", text="❌ Error: 'keyword' parameter is required")]

        result = await search_bids_by_keyword(keyword)
        return [TextContent(type="text", text=result)]

    elif name == "recommend_bids_for_dept":
        keyword = arguments.get("keyword")
        department_profile = arguments.get("department_profile")

        if not keyword:
            return [TextContent(type="text", text="❌ Error: 'keyword' parameter is required")]
        if not department_profile:
            return [TextContent(type="text", text="❌ Error: 'department_profile' parameter is required")]

        result = await search_bids_for_dept(keyword, department_profile)
        return [TextContent(type="text", text=result)]

    elif name == "analyze_bid_detail":
        file_url = arguments.get("file_url")
        filename = arguments.get("filename")
        department_profile = arguments.get("department_profile", "")

        if not file_url:
            return [TextContent(type="text", text="❌ Error: 'file_url' parameter is required")]
        if not filename:
            return [TextContent(type="text", text="❌ Error: 'filename' parameter is required")]

        result = await analyze_bid_detail(file_url, filename, department_profile)
        return [TextContent(type="text", text=result)]

    return [TextContent(type="text", text=f"❌ Unknown tool: {name}")]


async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
