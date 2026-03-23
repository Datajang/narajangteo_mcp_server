#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Nara MCP Server - Korean Government Procurement Bid Search
나라장터 입찰공고 검색 MCP 서버
"""

import sys
import os
import logging
from datetime import datetime, timedelta

import httpx
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

from .file_extractor import extract_text_from_url

# Configure logging to write to stderr
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("nara-mcp-server")

# Force UTF-8 encoding for Windows
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')

# API Configuration
BASE_URL = "http://apis.data.go.kr/1230000/ad/BidPublicInfoService"
ENDPOINT = "getBidPblancListInfoServcPPSSrch"
PRESPEC_API_URL = "http://apis.data.go.kr/1230000/ao/HrcspSsstndrdInfoService/getPublicPrcureThngInfoServcPPSSrch"


def get_api_key() -> str:
    load_dotenv()
    api_key = os.getenv("NARA_API_KEY", "")
    if api_key:
        return api_key
    raise ValueError(
        "NARA_API_KEY not found.\n"
        "Create .env file with: NARA_API_KEY=your_key\n"
        "Or set environment variable: set NARA_API_KEY=your_key"
    )


def get_prespec_api_key() -> str:
    load_dotenv()
    api_key = os.getenv("NARA_PRESPEC_API_KEY", "")
    if api_key:
        return api_key
    raise ValueError(
        "NARA_PRESPEC_API_KEY not found.\n"
        "Create .env file with: NARA_PRESPEC_API_KEY=your_key"
    )


def get_date_range(days: int = 7) -> tuple[int, int]:
    """
    Get date range for the last N days.
    Returns: (start_date, end_date) in YYYYMMDDHHMM format as integers
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    start_dt_int = int(start_date.strftime("%Y%m%d0000"))
    end_dt_int = int(end_date.strftime("%Y%m%d2359"))

    return start_dt_int, end_dt_int


def get_date_chunks(days: int, chunk_size: int = 15) -> list[tuple[int, int]]:
    """
    Split date range into chunks to work around API date range limits.
    Returns list of (start, end) tuples in YYYYMMDDHHMM format as integers.
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    chunks = []
    chunk_start = start_date
    while chunk_start < end_date:
        chunk_end = min(chunk_start + timedelta(days=chunk_size), end_date)
        chunks.append((
            int(chunk_start.strftime("%Y%m%d0000")),
            int(chunk_end.strftime("%Y%m%d2359")),
        ))
        chunk_start = chunk_end + timedelta(days=1)
    return chunks


def is_bid_open(close_datetime_str: str) -> bool:
    """
    Check if bid deadline is in the future.
    Handles multiple date formats returned by the API.
    """
    if not close_datetime_str or close_datetime_str == "N/A":
        return True
    for fmt in ("%Y%m%d%H%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y%m%d"):
        try:
            close_dt = datetime.strptime(close_datetime_str.strip(), fmt)
            return close_dt > datetime.now()
        except ValueError:
            continue
    return True


def filter_proposal_files(item: dict) -> list[tuple[str, str]]:
    """
    Filter files containing "제안요청서" or "제안" from API response.

    Args:
        item: API response item

    Returns:
        List of (url, filename) tuples for proposal files
    """
    proposal_files = []

    for i in range(1, 11):
        url_key = f"ntceSpecDocUrl{i}"
        name_key = f"ntceSpecFileNm{i}"

        url = item.get(url_key, "")
        filename = item.get(name_key, "")

        if url and filename:
            if "제안요청서" in filename or "제안" in filename:
                proposal_files.append((url, filename))

    return proposal_files


def filter_spec_doc_files(item: dict) -> list[tuple[str, str]]:
    """Extract specDocFileUrl1~5 from pre-spec API response."""
    files = []
    for i in range(1, 6):
        url = item.get(f"specDocFileUrl{i}", "")
        if url:
            files.append((url, f"규격문서 {i}"))
    return files


async def search_bids_by_keyword(keyword: str, service_key: str, prespec_service_key: str, days: int = 7) -> str:
    """
    Search for service-type bid notices AND preliminary specifications.

    Args:
        keyword: Search term for bid title
        service_key: API key for regular bids
        prespec_service_key: API key for pre-spec endpoint

    Returns:
        Formatted string with both bid notices and preliminary specifications
    """
    if not service_key:
        return (
            "❌ Error: NARA_API_KEY is required.\n"
            "Please set your API key in the session configuration or environment variable.\n"
            "Get your API key from: https://www.data.go.kr/\n"
            "Search for '나라장터 입찰정보' and register for the service."
        )

    # Ensure UTF-8 encoding
    if isinstance(keyword, bytes):
        keyword = keyword.decode('utf-8', errors='replace')
    else:
        keyword = keyword.encode('utf-8', errors='replace').decode('utf-8')

    date_chunks = get_date_chunks(days)
    start_date_str = str(date_chunks[0][0])[:8]
    end_date_str = str(date_chunks[-1][1])[:8]

    bid_url = f"{BASE_URL}/{ENDPOINT}"

    open_bids = []
    bid_total = 0
    open_prespecs = []
    prespec_total = 0
    prespec_errors = []

    if not prespec_service_key:
        prespec_errors.append("NARA_PRESPEC_API_KEY 미설정 — .env에 키를 추가하세요")

    async with httpx.AsyncClient(timeout=30.0) as client:
        for chunk_start, chunk_end in date_chunks:
            # Regular Bid Notices
            try:
                bid_params = {
                    "ServiceKey": service_key,
                    "type": "json",
                    "inqryDiv": "1",
                    "inqryBgnDt": chunk_start,
                    "inqryEndDt": chunk_end,
                    "bidNtceNm": keyword,
                    "numOfRows": "20",
                    "pageNo": "1"
                }
                bid_response = await client.get(bid_url, params=bid_params)
                bid_response.raise_for_status()
                bid_data = bid_response.json()
                bid_header = bid_data.get("response", {}).get("header", {})
                if bid_header.get("resultCode") == "00":
                    bid_body = bid_data.get("response", {}).get("body", {})
                    bid_items = bid_body.get("items")
                    bid_total += bid_body.get("totalCount", 0)
                    if bid_items and not isinstance(bid_items, str):
                        if isinstance(bid_items, list):
                            open_bids.extend(bid_items)
                        elif isinstance(bid_items, dict):
                            item = bid_items.get("item", [])
                            open_bids.extend([item] if isinstance(item, dict) else item)
            except Exception as e:
                logger.error(f"Error fetching bid notices (chunk {chunk_start}-{chunk_end}): {e}")

            # Preliminary Specifications
            if prespec_service_key:
                try:
                    prespec_params = {
                        "ServiceKey": prespec_service_key,
                        "type": "json",
                        "inqryDiv": "1",
                        "inqryBgnDt": chunk_start,
                        "inqryEndDt": chunk_end,
                        "prdctClsfcNoNm": keyword,
                        "numOfRows": "20",
                        "pageNo": "1"
                    }
                    prespec_response = await client.get(PRESPEC_API_URL, params=prespec_params)
                    if prespec_response.status_code == 404:
                        prespec_errors.append("HTTP 404 - 사전규격 API 엔드포인트를 찾을 수 없음")
                        logger.error("Pre-spec API 404: endpoint not found")
                        break
                    prespec_response.raise_for_status()
                    prespec_data = prespec_response.json()
                    prespec_header = prespec_data.get("response", {}).get("header", {})
                    if prespec_header.get("resultCode") == "00":
                        prespec_body = prespec_data.get("response", {}).get("body", {})
                        prespec_items = prespec_body.get("items")
                        prespec_total += prespec_body.get("totalCount", 0)
                        if prespec_items and not isinstance(prespec_items, str):
                            if isinstance(prespec_items, list):
                                open_prespecs.extend(prespec_items)
                            elif isinstance(prespec_items, dict):
                                item = prespec_items.get("item", [])
                                open_prespecs.extend([item] if isinstance(item, dict) else item)
                    else:
                        result_code = prespec_header.get("resultCode", "?")
                        result_msg = prespec_header.get("resultMsg", "")
                        prespec_errors.append(f"API 오류 코드 {result_code}: {result_msg}")
                except Exception as e:
                    if not prespec_errors:
                        prespec_errors.append(str(e))
                    logger.error(f"Error fetching pre-specs (chunk {chunk_start}-{chunk_end}): {e}")

    if not open_bids and not open_prespecs and not prespec_errors:
        return f"📭 No bid notices or preliminary specifications found for keyword: '{keyword}' in the last {days} days."

    # Build pre-spec lookup by registration number for cross-referencing
    prespec_docs_by_no = {
        item["bfSpecRgstNo"]: filter_spec_doc_files(item)
        for item in open_prespecs
        if item.get("bfSpecRgstNo") and filter_spec_doc_files(item)
    }

    # Format Results
    results = []

    # Section 1: Regular Bid Notices
    results.append(f"🔍 **일반 입찰 공고 (Regular Bids)**\n")
    results.append(f"Found {bid_total} bid notice(s) total, {len(open_bids)} retrieved\n")
    results.append(f"📅 Search period: {start_date_str} ~ {end_date_str} (last {days} days)\n")
    results.append("=" * 80 + "\n")

    if open_bids:
        for idx, item in enumerate(open_bids, 1):
            bid_name = item.get("bidNtceNm", "N/A")
            bid_no = item.get("bidNtceNo", "N/A")
            deadline = item.get("bidClseDt", "N/A")
            demand_org = item.get("dminsttNm", "N/A")

            # Budget info
            bdgt_amt = item.get("bdgtAmt", "0")
            presmp_prce = item.get("presmptPrce", "0")
            budget = bdgt_amt if bdgt_amt and str(bdgt_amt) != "0" else presmp_prce if presmp_prce and str(presmp_prce) != "0" else "0"
            try:
                budget_formatted = f"{int(budget):,}원" if budget != "0" else "미공개"
            except (ValueError, TypeError):
                budget_formatted = "미공개"

            status = "✅ 진행중" if is_bid_open(item.get("bidClseDt", "")) else "🔴 마감"
            results.append(f"\n## {idx}. {bid_name}\n")
            results.append(f"   📌 공고번호: {bid_no}\n")
            results.append(f"   🏢 수요기관: {demand_org}\n")
            results.append(f"   💰 예산: {budget_formatted}\n")
            results.append(f"   ⏰ 마감일시: {deadline} ({status})\n")

            proposal_files = filter_proposal_files(item)
            bf_spec_no = item.get("bfSpecRgstNo", "")
            prespec_files = []
            if not proposal_files and bf_spec_no:
                prespec_files = prespec_docs_by_no.get(bf_spec_no, [])

            if proposal_files:
                results.append(f"   📎 제안요청서:\n")
                for url, filename in proposal_files:
                    results.append(f"      - {filename}: {url}\n")
            elif prespec_files:
                results.append(f"   📋 제안요청정보 (사전규격 {bf_spec_no}):\n")
                for url, label in prespec_files:
                    results.append(f"      - {label}: {url}\n")
            elif bf_spec_no:
                results.append(f"   📎 제안요청서: 없음 (사전규격 {bf_spec_no} 참조)\n")
            else:
                results.append(f"   📎 제안요청서: 없음\n")
            results.append("\n" + "-" * 80 + "\n")
    else:
        results.append("No open bid notices found.\n\n")

    # Section 2: Preliminary Specifications
    results.append("\n" + "=" * 80 + "\n")
    results.append(f"📋 **사전규격 공고 (Preliminary Specifications)**\n")
    results.append(f"Found {prespec_total} pre-spec(s) total, {len(open_prespecs)} retrieved\n")
    results.append("=" * 80 + "\n")

    if open_prespecs:
        for idx, item in enumerate(open_prespecs, 1):
            spec_name = item.get("prdctClsfcNoNm", "N/A")
            spec_no = item.get("bfSpecRgstNo", "N/A")
            deadline = item.get("opninRgstClseDt", "N/A")
            agency = item.get("orderInsttNm", "N/A")

            budget_amt = item.get("asignBdgtAmt", "0")
            try:
                budget_formatted = f"{int(budget_amt):,}원" if budget_amt and budget_amt != "0" else "미공개"
            except (ValueError, TypeError):
                budget_formatted = "미공개"

            status = "✅ 진행중" if is_bid_open(item.get("opninRgstClseDt", "")) else "🔴 마감"
            results.append(f"\n## {idx}. 📋 [사전규격] {spec_name}\n")
            results.append(f"   📌 사전규격번호: {spec_no}\n")
            results.append(f"   🏢 발주기관: {agency}\n")
            results.append(f"   💰 배정예산: {budget_formatted}\n")
            results.append(f"   ⏰ 의견마감일시: {deadline} ({status})\n")

            spec_files = filter_spec_doc_files(item)
            if spec_files:
                results.append(f"   📎 규격문서:\n")
                for url, label in spec_files:
                    results.append(f"      - {label}: {url}\n")
            else:
                results.append(f"   📎 규격문서: 없음\n")
            results.append("\n" + "-" * 80 + "\n")
    elif prespec_errors:
        results.append(f"⚠️ 사전규격 오류: {prespec_errors[0]}\n")
    else:
        results.append("No open preliminary specifications found.\n")

    return "".join(results)


async def search_bids_for_dept(keyword: str, department_profile: str, service_key: str, prespec_service_key: str, days: int = 7) -> str:
    """
    Department-specific integrated search with up to 60 results.

    Args:
        keyword: Search keyword
        department_profile: Team/department description
        service_key: API key for regular bids
        prespec_service_key: API key for pre-spec endpoint

    Returns:
        60 results with department context and LLM instructions
    """
    if not service_key:
        return (
            "❌ Error: NARA_API_KEY is required.\n"
            "Please set your API key in the session configuration or environment variable.\n"
            "Get your API key from: https://www.data.go.kr/"
        )

    if isinstance(keyword, bytes):
        keyword = keyword.decode('utf-8', errors='replace')
    else:
        keyword = keyword.encode('utf-8', errors='replace').decode('utf-8')

    date_chunks = get_date_chunks(days)
    bid_url = f"{BASE_URL}/{ENDPOINT}"

    open_bids = []
    bid_total = 0
    open_prespecs = []
    prespec_total = 0
    prespec_errors = []

    if not prespec_service_key:
        prespec_errors.append("NARA_PRESPEC_API_KEY 미설정 — .env에 키를 추가하세요")

    async with httpx.AsyncClient(timeout=30.0) as client:
        for chunk_start, chunk_end in date_chunks:
            # Regular Bid Notices (30)
            try:
                bid_params = {
                    "ServiceKey": service_key,
                    "type": "json",
                    "inqryDiv": "1",
                    "inqryBgnDt": chunk_start,
                    "inqryEndDt": chunk_end,
                    "bidNtceNm": keyword,
                    "numOfRows": "30",
                    "pageNo": "1"
                }
                bid_response = await client.get(bid_url, params=bid_params)
                bid_response.raise_for_status()
                bid_data = bid_response.json()
                bid_header = bid_data.get("response", {}).get("header", {})
                if bid_header.get("resultCode") == "00":
                    bid_body = bid_data.get("response", {}).get("body", {})
                    bid_items = bid_body.get("items")
                    bid_total += bid_body.get("totalCount", 0)
                    if bid_items and not isinstance(bid_items, str):
                        if isinstance(bid_items, list):
                            open_bids.extend(bid_items)
                        elif isinstance(bid_items, dict):
                            item = bid_items.get("item", [])
                            open_bids.extend([item] if isinstance(item, dict) else item)
            except Exception as e:
                logger.error(f"Error in dept search (bids, chunk {chunk_start}-{chunk_end}): {e}")

            # Preliminary Specifications (30)
            if prespec_service_key:
                try:
                    prespec_params = {
                        "ServiceKey": prespec_service_key,
                        "type": "json",
                        "inqryDiv": "1",
                        "inqryBgnDt": chunk_start,
                        "inqryEndDt": chunk_end,
                        "prdctClsfcNoNm": keyword,
                        "numOfRows": "30",
                        "pageNo": "1"
                    }
                    prespec_response = await client.get(PRESPEC_API_URL, params=prespec_params)
                    if prespec_response.status_code == 404:
                        prespec_errors.append("HTTP 404 - 사전규격 API 엔드포인트를 찾을 수 없음")
                        logger.error("Pre-spec API 404: endpoint not found")
                        break
                    prespec_response.raise_for_status()
                    prespec_data = prespec_response.json()
                    prespec_header = prespec_data.get("response", {}).get("header", {})
                    if prespec_header.get("resultCode") == "00":
                        prespec_body = prespec_data.get("response", {}).get("body", {})
                        prespec_items = prespec_body.get("items")
                        prespec_total += prespec_body.get("totalCount", 0)
                        if prespec_items and not isinstance(prespec_items, str):
                            if isinstance(prespec_items, list):
                                open_prespecs.extend(prespec_items)
                            elif isinstance(prespec_items, dict):
                                item = prespec_items.get("item", [])
                                open_prespecs.extend([item] if isinstance(item, dict) else item)
                    else:
                        result_code = prespec_header.get("resultCode", "?")
                        result_msg = prespec_header.get("resultMsg", "")
                        prespec_errors.append(f"API 오류 코드 {result_code}: {result_msg}")
                except Exception as e:
                    if not prespec_errors:
                        prespec_errors.append(str(e))
                    logger.error(f"Error in dept search (prespecs, chunk {chunk_start}-{chunk_end}): {e}")

    if not open_bids and not open_prespecs and not prespec_errors:
        return f"📭 No bid notices or preliminary specifications found for keyword: '{keyword}'"

    # Build pre-spec lookup by registration number for cross-referencing
    prespec_docs_by_no = {
        item["bfSpecRgstNo"]: filter_spec_doc_files(item)
        for item in open_prespecs
        if item.get("bfSpecRgstNo") and filter_spec_doc_files(item)
    }

    # Format Results with LLM Instructions
    results = [
        f"🎯 Department-Filtered Integrated Search Results",
        f"",
        f"📋 **Department Profile:** {department_profile}",
        f"🔍 **Keyword:** {keyword}",
        f"📊 **Results:**",
        f"  - Regular Bids: {len(open_bids)} open (out of {bid_total} total)",
        f"  - Pre-Specs: {len(open_prespecs)} open (out of {prespec_total} total)"
        + (f" ⚠️ [{prespec_errors[0]}]" if prespec_errors else ""),
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

        bdgt_amt = item.get("bdgtAmt", "0")
        presmp_prce = item.get("presmptPrce", "0")
        budget = bdgt_amt if bdgt_amt and str(bdgt_amt) != "0" else presmp_prce if presmp_prce and str(presmp_prce) != "0" else "0"
        try:
            budget_formatted = f"{int(budget):,}원" if budget != "0" else "미공개"
        except (ValueError, TypeError):
            budget_formatted = "미공개"

        status = "✅ 진행중" if is_bid_open(item.get("bidClseDt", "")) else "🔴 마감"
        results.append(f"### [BID-{idx}] {bid_name}")
        results.append(f"- 공고번호: {bid_no}")
        results.append(f"- 수요기관: {demand_org}")
        results.append(f"- 예산: {budget_formatted}")
        results.append(f"- 마감일시: {deadline} ({status})")
        if bid_url:
            results.append(f"- 공고 URL: {bid_url}")

        proposal_files = filter_proposal_files(item)
        bf_spec_no = item.get("bfSpecRgstNo", "")
        prespec_files = []
        if not proposal_files and bf_spec_no:
            prespec_files = prespec_docs_by_no.get(bf_spec_no, [])

        if proposal_files:
            results.append(f"- 제안요청서:")
            for url, filename in proposal_files:
                results.append(f"  - {filename}: {url}")
        elif prespec_files:
            results.append(f"- 제안요청정보 (사전규격 {bf_spec_no}):")
            for url, label in prespec_files:
                results.append(f"  - {label}: {url}")
        elif bf_spec_no:
            results.append(f"- 제안요청서: 없음 (사전규격 {bf_spec_no} 참조)")
        results.append("")

    # Section 2: Preliminary Specifications
    results.append(f"\n## Preliminary Specifications ({len(open_prespecs)} open)\n")
    for idx, item in enumerate(open_prespecs, 1):
        spec_name = item.get("prdctClsfcNoNm", "N/A")
        spec_no = item.get("bfSpecRgstNo", "N/A")
        deadline = item.get("opninRgstClseDt", "N/A")
        agency = item.get("orderInsttNm", "N/A")

        budget_amt = item.get("asignBdgtAmt", "0")
        try:
            budget_formatted = f"{int(budget_amt):,}원" if budget_amt and budget_amt != "0" else "미공개"
        except (ValueError, TypeError):
            budget_formatted = "미공개"

        status = "✅ 진행중" if is_bid_open(item.get("opninRgstClseDt", "")) else "🔴 마감"
        results.append(f"### [PRESPEC-{idx}] 📋 [사전규격] {spec_name}")
        results.append(f"- 사전규격번호: {spec_no}")
        results.append(f"- 발주기관: {agency}")
        results.append(f"- 배정예산: {budget_formatted}")
        results.append(f"- 의견마감일시: {deadline} ({status})")

        spec_files = filter_spec_doc_files(item)
        if spec_files:
            results.append(f"- 규격문서:")
            for url, label in spec_files:
                results.append(f"  - {label}: {url}")
        results.append("")

    if not open_prespecs and prespec_errors:
        results.append(f"⚠️ 사전규격 오류: {prespec_errors[0]}")
        results.append("")

    return "\n".join(results)


def create_server():
    """Create and configure the Nara MCP server."""

    server = FastMCP("Nara MCP Server")

    @server.tool()
    async def get_bids_by_keyword(
        keyword: str,
        days: int = 7,
    ) -> str:
        """
        Search Korean government procurement notices (나라장터).
        Returns BOTH regular bid notices (입찰공고) AND preliminary specifications (사전규격)
        for service-type (용역) projects including consulting, development, and SI.

        Args:
            keyword: Search keyword for bid title (공고명).
                     Examples: '인공지능', 'AI', '플랫폼', '시스템 구축', etc.
            days: Search window in days from today (default: 7).
                  Increase for older bids, e.g. 30, 60, 90.

        Returns:
            Formatted string with bid information
        """
        if not keyword:
            return "❌ Error: 'keyword' parameter is required"

        service_key = get_api_key()
        try:
            prespec_key = get_prespec_api_key()
        except ValueError:
            prespec_key = ""
        return await search_bids_by_keyword(keyword, service_key, prespec_key, days=days)

    @server.tool()
    async def recommend_bids_for_dept(
        keyword: str,
        department_profile: str,
        days: int = 7,
    ) -> str:
        """
        Search government procurement notices with department context for personalized recommendations.
        Returns up to 60 results (30 regular bids + 30 pre-specs) with analysis instructions.
        LLM can flexibly present Top N items or all relevant items based on user's request.
        Prioritizes items with non-zero budgets.

        Args:
            keyword: Search keyword (e.g., 'AI', 'Cloud', '플랫폼')
            department_profile: Description of your team/department.
                               Examples: 'UI/UX 디자인팀', 'Database Migration Unit',
                                        'AI/ML 개발팀', '클라우드 인프라팀'
            days: Search window in days from today (default: 7).
                  Increase for older bids, e.g. 30, 60, 90.

        Returns:
            Formatted recommendations with strategic analysis
        """
        if not keyword:
            return "❌ Error: 'keyword' parameter is required"
        if not department_profile:
            return "❌ Error: 'department_profile' parameter is required"

        service_key = get_api_key()
        try:
            prespec_key = get_prespec_api_key()
        except ValueError:
            prespec_key = ""
        return await search_bids_for_dept(keyword, department_profile, service_key, prespec_key, days=days)

    @server.tool()
    async def analyze_bid_detail(
        file_url: str,
        filename: str,
        department_profile: str = "",
    ) -> str:
        """
        Download and extract text from bid attachment (RFP/제안요청서) for strategic analysis.
        Supports HWP, HWPX, PDF, DOCX, XLSX, and ZIP files.
        ZIP files are processed with priority: 제안요청서 > 과업지시서 > .hwp > .pdf

        Args:
            file_url: Attachment URL (ntceSpecDocUrl1 from search results)
            filename: Filename (ntceSpecFileNm1 from search results)
            department_profile: Optional - Your team description for strategic analysis.
                               If provided, response includes analysis prompts for Fit Score,
                               Core Tasks, Winning Strategy, and Risk Factors.

        Returns:
            Extracted document text with optional analysis prompts
        """
        if not file_url:
            return "❌ Error: 'file_url' parameter is required"
        if not filename:
            return "❌ Error: 'filename' parameter is required"

        try:
            extracted_text = await extract_text_from_url(file_url, filename)

            results = [
                f"# 📄 Bid Document Analysis",
                f"",
                f"**File:** {filename}",
                f"**Source:** {file_url}",
                f""
            ]

            if department_profile:
                results.extend([
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
            logger.error(f"Error analyzing bid detail: {e}")
            return f"❌ Failed to analyze bid document: {str(e)}\n\nManual link: {file_url}"

    # Add a resource
    @server.resource("info://nara-procurement")
    def nara_info() -> str:
        """Information about Nara procurement bid service."""
        return (
            "Nara MCP Server provides access to Korean government procurement bids (나라장터).\n"
            "Search for service-type (용역) projects including consulting, development, and SI.\n"
            "Data is sourced from the Korea Public Procurement Service API."
        )

    return server


def main():
    """
    CLI entry point for local STDIO mode.

    This function is used by:
    1. pyproject.toml [project.scripts] nara-server command
    2. python -m nara_server.server

    For Smithery deployment, use: uv run start (HTTP transport)
    """
    mcp_server = create_server()
    mcp_server.run(transport="stdio")


if __name__ == "__main__":
    main()
