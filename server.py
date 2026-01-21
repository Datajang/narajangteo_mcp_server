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
PRESPEC_ENDPOINT = "getBfSpecRgstSttusListInfoServcPPSSrch"


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
    Search for service-type bid notices AND preliminary specifications.
    Returns both regular bids and pre-specs in separate sections.

    Args:
        keyword: Search term for bid title / pre-spec title

    Returns:
        Formatted string with both bid notices and preliminary specifications
    """
    # Ensure keyword is properly encoded as UTF-8
    if isinstance(keyword, bytes):
        keyword = keyword.decode('utf-8', errors='replace')
    else:
        keyword = keyword.encode('utf-8', errors='replace').decode('utf-8')

    start_date, end_date = get_date_range_for_last_month()
    start_date_str = str(start_date)[:8]
    end_date_str = str(end_date)[:8]

    # ========== SECTION 1: Regular Bid Notices ==========
    bid_params = {
        "ServiceKey": SERVICE_KEY,
        "type": "json",
        "inqryDiv": "1",
        "inqryBgnDt": start_date,
        "inqryEndDt": end_date,
        "bidNtceNm": keyword,
        "numOfRows": "20",
        "pageNo": "1"
    }
    bid_url = f"{BASE_URL}/{ENDPOINT}"

    open_bids = []
    bid_total = 0
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            bid_response = await client.get(bid_url, params=bid_params)
            bid_response.raise_for_status()
            bid_data = bid_response.json()

        bid_header = bid_data.get("response", {}).get("header", {})
        if bid_header.get("resultCode") == "00":
            bid_body = bid_data.get("response", {}).get("body", {})
            bid_items = bid_body.get("items")
            bid_total = bid_body.get("totalCount", 0)

            if bid_items and not isinstance(bid_items, str):
                if isinstance(bid_items, list):
                    item_list = bid_items
                elif isinstance(bid_items, dict):
                    item_list = bid_items.get("item", [])
                    if isinstance(item_list, dict):
                        item_list = [item_list]
                else:
                    item_list = []

                open_bids = [item for item in item_list if is_bid_open(item.get("bidClseDt", ""))]
    except Exception:
        pass  # Continue to pre-spec search even if bid search fails

    # ========== SECTION 2: Preliminary Specifications ==========
    prespec_params = {
        "ServiceKey": SERVICE_KEY,
        "type": "json",
        "inqryDiv": "1",
        "inqryBgnDt": start_date,
        "inqryEndDt": end_date,
        "bfSpecNm": keyword,  # Different parameter name!
        "numOfRows": "20",
        "pageNo": "1"
    }
    prespec_url = f"{BASE_URL}/{PRESPEC_ENDPOINT}"

    open_prespecs = []
    prespec_total = 0
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            prespec_response = await client.get(prespec_url, params=prespec_params)
            prespec_response.raise_for_status()
            prespec_data = prespec_response.json()

        prespec_header = prespec_data.get("response", {}).get("header", {})
        if prespec_header.get("resultCode") == "00":
            prespec_body = prespec_data.get("response", {}).get("body", {})
            prespec_items = prespec_body.get("items")
            prespec_total = prespec_body.get("totalCount", 0)

            if prespec_items and not isinstance(prespec_items, str):
                if isinstance(prespec_items, list):
                    item_list = prespec_items
                elif isinstance(prespec_items, dict):
                    item_list = prespec_items.get("item", [])
                    if isinstance(item_list, dict):
                        item_list = [item_list]
                else:
                    item_list = []

                open_prespecs = [item for item in item_list if is_bid_open(item.get("opnEndDt", ""))]
    except Exception:
        pass  # Continue even if pre-spec search fails

    # ========== Check if both searches returned nothing ==========
    if not open_bids and not open_prespecs:
        return f"📭 No bid notices or preliminary specifications found for keyword: '{keyword}' in the last 7 days."

    # ========== Format Results ==========
    results = []

    # Section 1: Regular Bid Notices
    results.append(f"🔍 **일반 입찰 공고 (Regular Bids)**\n")
    results.append(f"Found {bid_total} bid notice(s) total, {len(open_bids)} still open\n")
    results.append(f"📅 Search period: {start_date_str} ~ {end_date_str}\n")
    results.append("=" * 80 + "\n")

    if open_bids:
        for idx, item in enumerate(open_bids, 1):
            bid_name = item.get("bidNtceNm", "N/A")
            bid_no = item.get("bidNtceNo", "N/A")
            deadline = item.get("bidClseDt", "N/A")
            spec_url = item.get("ntceSpecDocUrl1", "")
            demand_org = item.get("dminsttNm", "N/A")

            # Budget info
            bdgt_amt = item.get("bdgtAmt", "0")
            presmp_prce = item.get("presmptPrce", "0")
            if bdgt_amt and str(bdgt_amt) != "0":
                budget = bdgt_amt
            elif presmp_prce and str(presmp_prce) != "0":
                budget = presmp_prce
            else:
                budget = "0"
            try:
                budget_formatted = f"{int(budget):,}원" if budget != "0" else "미공개"
            except (ValueError, TypeError):
                budget_formatted = "미공개"

            results.append(f"\n## {idx}. {bid_name}\n")
            results.append(f"   📌 공고번호: {bid_no}\n")
            results.append(f"   🏢 수요기관: {demand_org}\n")
            results.append(f"   💰 예산: {budget_formatted}\n")
            results.append(f"   ⏰ 마감일시: {deadline}\n")
            if spec_url:
                results.append(f"   📎 제안요청서: {spec_url}\n")
            else:
                results.append(f"   📎 제안요청서: 없음\n")
            results.append("\n" + "-" * 80 + "\n")
    else:
        results.append("No open bid notices found.\n\n")

    # Section 2: Preliminary Specifications
    results.append("\n" + "=" * 80 + "\n")
    results.append(f"📋 **사전규격 공고 (Preliminary Specifications)**\n")
    results.append(f"Found {prespec_total} pre-spec(s) total, {len(open_prespecs)} still open\n")
    results.append("=" * 80 + "\n")

    if open_prespecs:
        for idx, item in enumerate(open_prespecs, 1):
            spec_name = item.get("bfSpecNm", "N/A")
            spec_no = item.get("bfSpecRgstNo", "N/A")
            deadline = item.get("opnEndDt", "N/A")
            agency = item.get("ordInsttNm", "N/A")
            spec_url = item.get("ntceSpecDocUrl1", "")

            # Budget info (pre-spec uses different field)
            budget_amt = item.get("asignBdgtAmt", "0")
            try:
                budget_formatted = f"{int(budget_amt):,}원" if budget_amt and budget_amt != "0" else "미공개"
            except (ValueError, TypeError):
                budget_formatted = "미공개"

            results.append(f"\n## {idx}. {spec_name}\n")
            results.append(f"   📌 사전규격번호: {spec_no}\n")
            results.append(f"   🏢 발주기관: {agency}\n")
            results.append(f"   💰 배정예산: {budget_formatted}\n")
            results.append(f"   ⏰ 의견마감일시: {deadline}\n")
            if spec_url:
                results.append(f"   📎 제안요청서: {spec_url}\n")
            else:
                results.append(f"   📎 제안요청서: 없음\n")
            results.append("\n" + "-" * 80 + "\n")
    else:
        results.append("No open preliminary specifications found.\n")

    return "".join(results)


async def search_bids_for_dept(keyword: str, department_profile: str) -> str:
    """
    부서 맞춤형 통합 검색 (일반 입찰 + 사전규격)
    최대 60개 결과 (입찰 30 + 사전규격 30)를 LLM에게 전달
    LLM이 사용자 요청에 따라 유연하게 대응 (Top N 또는 전체)

    Args:
        keyword: 검색 키워드
        department_profile: 부서/팀 설명

    Returns:
        60개 결과 + 부서 프로필 컨텍스트 + LLM 지시문
    """
    if isinstance(keyword, bytes):
        keyword = keyword.decode('utf-8', errors='replace')
    else:
        keyword = keyword.encode('utf-8', errors='replace').decode('utf-8')

    start_date, end_date = get_date_range_for_last_month()

    # ========== API 1: Regular Bid Notices (30개) ==========
    bid_params = {
        "ServiceKey": SERVICE_KEY,
        "type": "json",
        "inqryDiv": "1",
        "inqryBgnDt": start_date,
        "inqryEndDt": end_date,
        "bidNtceNm": keyword,
        "numOfRows": "30",
        "pageNo": "1"
    }
    bid_url = f"{BASE_URL}/{ENDPOINT}"

    open_bids = []
    bid_total = 0
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            bid_response = await client.get(bid_url, params=bid_params)
            bid_response.raise_for_status()
            bid_data = bid_response.json()

        bid_header = bid_data.get("response", {}).get("header", {})
        if bid_header.get("resultCode") == "00":
            bid_body = bid_data.get("response", {}).get("body", {})
            bid_items = bid_body.get("items")
            bid_total = bid_body.get("totalCount", 0)

            if bid_items and not isinstance(bid_items, str):
                if isinstance(bid_items, list):
                    item_list = bid_items
                elif isinstance(bid_items, dict):
                    item_list = bid_items.get("item", [])
                    if isinstance(item_list, dict):
                        item_list = [item_list]
                else:
                    item_list = []

                open_bids = [item for item in item_list if is_bid_open(item.get("bidClseDt", ""))]
    except Exception:
        pass

    # ========== API 2: Preliminary Specifications (30개) ==========
    prespec_params = {
        "ServiceKey": SERVICE_KEY,
        "type": "json",
        "inqryDiv": "1",
        "inqryBgnDt": start_date,
        "inqryEndDt": end_date,
        "bfSpecNm": keyword,
        "numOfRows": "30",
        "pageNo": "1"
    }
    prespec_url = f"{BASE_URL}/{PRESPEC_ENDPOINT}"

    open_prespecs = []
    prespec_total = 0
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            prespec_response = await client.get(prespec_url, params=prespec_params)
            prespec_response.raise_for_status()
            prespec_data = prespec_response.json()

        prespec_header = prespec_data.get("response", {}).get("header", {})
        if prespec_header.get("resultCode") == "00":
            prespec_body = prespec_data.get("response", {}).get("body", {})
            prespec_items = prespec_body.get("items")
            prespec_total = prespec_body.get("totalCount", 0)

            if prespec_items and not isinstance(prespec_items, str):
                if isinstance(prespec_items, list):
                    item_list = prespec_items
                elif isinstance(prespec_items, dict):
                    item_list = prespec_items.get("item", [])
                    if isinstance(item_list, dict):
                        item_list = [item_list]
                else:
                    item_list = []

                open_prespecs = [item for item in item_list if is_bid_open(item.get("opnEndDt", ""))]
    except Exception:
        pass

    if not open_bids and not open_prespecs:
        return f"📭 No bid notices or preliminary specifications found for keyword: '{keyword}'"

    # ========== Format Results with LLM Instructions ==========
    results = [
        f"🎯 Department-Filtered Integrated Search Results",
        f"",
        f"📋 **Department Profile:** {department_profile}",
        f"🔍 **Keyword:** {keyword}",
        f"📊 **Results:**",
        f"  - Regular Bids: {len(open_bids)} open (out of {bid_total} total)",
        f"  - Pre-Specs: {len(open_prespecs)} open (out of {prespec_total} total)",
        f"",
        f"=" * 80,
        f"",
        f"**Instructions for LLM:**",
        f"Analyze BOTH regular bids AND preliminary specifications below for relevance to the department profile.",
        f"**Prioritize items with non-zero budget values.**",
        f"",
        f"Based on the user's request:",
        f"  - If they ask for Top 5 or specific number: Select and present the most relevant items",
        f"  - If they ask for all relevant items: Present all items sorted by relevance",
        f"",
        f"For each item you present, include:",
        f"  1. Type (Regular Bid or Pre-Spec) - Use the [BID-N] or [PRESPEC-N] prefix from the data",
        f"  2. Relevance reason (why it fits the department)",
        f"  3. Budget amount",
        f"  4. URL (공고 URL or 제안요청서 URL)",
        f"",
        f"=" * 80,
        f""
    ]

    # Section 1: Regular Bids
    results.append(f"## Regular Bids ({len(open_bids)} open)\n")
    for idx, item in enumerate(open_bids, 1):
        bid_name = item.get("bidNtceNm", "N/A")
        bid_no = item.get("bidNtceNo", "N/A")
        deadline = item.get("bidClseDt", "N/A")
        demand_org = item.get("dminsttNm", "N/A")
        bid_url = item.get("bidNtceDtlUrl", "")
        spec_url = item.get("ntceSpecDocUrl1", "")

        # Budget
        bdgt_amt = item.get("bdgtAmt", "0")
        presmp_prce = item.get("presmptPrce", "0")
        if bdgt_amt and str(bdgt_amt) != "0":
            budget = bdgt_amt
        elif presmp_prce and str(presmp_prce) != "0":
            budget = presmp_prce
        else:
            budget = "0"
        try:
            budget_formatted = f"{int(budget):,}원" if budget != "0" else "미공개"
        except (ValueError, TypeError):
            budget_formatted = "미공개"

        results.append(f"### [BID-{idx}] {bid_name}")
        results.append(f"- 공고번호: {bid_no}")
        results.append(f"- 수요기관: {demand_org}")
        results.append(f"- 예산: {budget_formatted}")
        results.append(f"- 마감일시: {deadline}")
        if bid_url:
            results.append(f"- 공고 URL: {bid_url}")
        if spec_url:
            results.append(f"- 제안요청서 URL: {spec_url}")
        results.append("")

    # Section 2: Preliminary Specifications
    results.append(f"\n## Preliminary Specifications ({len(open_prespecs)} open)\n")
    for idx, item in enumerate(open_prespecs, 1):
        spec_name = item.get("bfSpecNm", "N/A")
        spec_no = item.get("bfSpecRgstNo", "N/A")
        deadline = item.get("opnEndDt", "N/A")
        agency = item.get("ordInsttNm", "N/A")
        spec_url = item.get("ntceSpecDocUrl1", "")

        # Budget (pre-spec)
        budget_amt = item.get("asignBdgtAmt", "0")
        try:
            budget_formatted = f"{int(budget_amt):,}원" if budget_amt and budget_amt != "0" else "미공개"
        except (ValueError, TypeError):
            budget_formatted = "미공개"

        results.append(f"### [PRESPEC-{idx}] {spec_name}")
        results.append(f"- 사전규격번호: {spec_no}")
        results.append(f"- 발주기관: {agency}")
        results.append(f"- 배정예산: {budget_formatted}")
        results.append(f"- 의견마감일시: {deadline}")
        if spec_url:
            results.append(f"- 제안요청서 URL: {spec_url}")
        results.append("")

    return "\n".join(results)


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
                "Search Korean government procurement notices (나라장터) for the last 30 days. "
                "Returns BOTH regular bid notices (입찰공고) AND preliminary specifications (사전규격) "
                "for service-type (용역) projects including consulting, development, and SI."
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
                "Search government procurement notices with department context for personalized recommendations. "
                "Returns up to 60 results (30 regular bids + 30 pre-specs) with analysis instructions. "
                "LLM can flexibly present Top N items or all relevant items based on user's request. "
                "Prioritizes items with non-zero budgets."
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
