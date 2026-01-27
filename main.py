"""
Nara MCP Server - Entry Point

A Model Context Protocol server for searching Korean government
procurement bids from G2B (나라장터).

Features:
- Integrated search: Regular bids + Pre-specs
- Budget information included
- File extraction (HWP, PDF, DOCX, etc.)
- Smithery deployment support

Usage:
    python main.py

Environment Variables:
    NARA_API_KEY - Your API key from data.go.kr (required)

Get your API key:
    1. Visit https://www.data.go.kr/
    2. Search for '조달청_나라장터 입찰공고정보서비스'
    3. Apply for access and get your ServiceKey

Author: Datajang
Version: 1.1.0
License: MIT
"""

from nara_server.server import main

if __name__ == "__main__":
    main()
