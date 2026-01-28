# Nara MCP Server (나라장터 입찰공고 검색)

MCP server for searching Korean government procurement bid notices from G2B (나라장터 - Nara Jangteo).

## Features

- 🔍 **통합 검색**: 최근 7일간 용역 입찰공고 + 사전규격을 키워드로 검색
- 💰 **예산 정보**: 모든 검색 결과에 예산 금액 표시
- 📅 **자동 필터링**: 마감되지 않은 공고만 자동 필터링
- 📎 **파일 추출**: 제안요청서(RFP) 자동 다운로드 및 텍스트 추출
- 🗂️ **스마트 필터링**: 제안요청서/과업지시서 파일만 자동 선별
- 🏢 **맞춤형 추천**: 부서 프로필 기반 유연한 추천 (Top N 또는 전체 목록)
- 📄 **다형식 지원**: HWP, HWPX, PDF, DOCX, XLSX, ZIP 파일 자동 처리
- 🎯 **전략 분석**: 첨부파일 기반 입찰 전략 제안

## Quick Start

Get started in 3 steps:

1. **Install from PyPI**
   ```bash
   pip install nara-mcp-server
   ```

2. **Get API key**
   Visit [공공데이터포털](https://www.data.go.kr/) and search for "조달청_나라장터 입찰공고정보서비스"

3. **Configure Claude Desktop**
   Add to `claude_desktop_config.json`:
   ```json
   {
     "mcpServers": {
       "nara-jangteo": {
         "command": "uvx",
       "args": [
           "--python",
           "3.11",
           "--from",
           "nara-mcp-server",
           "nara-server"
         ],
         "env": {
           "NARA_API_KEY": "발급받은 API KEY",
           "UV_LINK_MODE": "copy"
         }
       }
     }
   }
   ```

4. **Start using!**
   Restart Claude Desktop and ask: "나라장터에서 'AI' 키워드로 입찰공고를 검색해줘"

## Prerequisites

### 1. API 키 발급 (필수)

나라장터 API를 사용하려면 공공데이터포털에서 API 키를 발급받아야 합니다.

**발급 절차:**
1. [공공데이터포털](https://www.data.go.kr/) 접속 및 회원가입
2. 검색창에 **"조달청_나라장터 입찰공고정보서비스"** 검색
3. **"조달청_나라장터 입찰공고정보서비스"** 선택
4. **활용신청** 클릭 (즉시 승인 또는 승인 대기)
5. **마이페이지 > 개발계정** 에서 ServiceKey 확인 (일반 인증키 Decoding을 사용하면 됩니다.)

### 2. Python 환경

- Python 3.10 이상 필요

## Installation

### Option 1: From PyPI (Recommended)

The simplest way to install:

```bash
pip install nara-mcp-server
```

**Note**: This installs the `nara-server` command globally for easy access.

### Option 2: From Source (For Development)

If you want to contribute or modify the code:

```bash
git clone https://github.com/Datajang/narajangteo_mcp_server.git
cd narajangteo_mcp_server
pip install -e .
```

## Configuration

### Using .env File (Recommended for Development)

Create a `.env` file in the project root:

```bash
# .env
NARA_API_KEY=your_service_key_from_data_go_kr
```

The `.env` file is automatically loaded when running the server.

### Claude Desktop Configuration

**설정 파일 위치:**
- **MacOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%/Claude/claude_desktop_config.json`

**Recommended: Using installed package**

```json
{
  "mcpServers": {
    "nara-jangteo": {
      "command": "uvx",
    "args": [
        "--python",
        "3.11",
        "--from",
        "nara-mcp-server",
        "nara-server"
      ],
      "env": {
        "NARA_API_KEY": "발급받은 API KEY",
        "UV_LINK_MODE": "copy"
      }
    }
  }
}
```

**Alternative: Using Python directly (if not installed globally)**

```json
{
  "mcpServers": {
    "nara-jangteo": {
      "command": "uvx",
    "args": [
        "--python",
        "3.11",
        "--from",
        "nara-mcp-server",
        "nara-server"
      ],
      "env": {
        "NARA_API_KEY": "발급받은 API KEY",
        "UV_LINK_MODE": "copy"
      }
    }
  }
}
```

**중요 사항:**
- PyPI 설치 시 `nara-server` 명령어가 자동으로 등록됩니다
- `NARA_API_KEY`에 발급받은 ServiceKey 입력
- Claude Desktop 재시작 필요

### Other MCP Clients

Continue, Cline 등 다른 MCP 클라이언트도 동일한 방식으로 설정 가능합니다.

## Development & Testing

### Using .env File (Recommended)

For local development, create a `.env` file:

```bash
# .env
NARA_API_KEY=your_service_key_here
```

The `.env` file is automatically loaded and **not tracked by git** (.gitignore).

**Benefits:**
- No need to set environment variables every time
- Works across all terminals
- Easier for MCP Inspector testing

**Example workflow:**
```bash
# 1. Copy example file
cp .env.example .env

# 2. Edit .env and add your API key
# NARA_API_KEY=your_actual_key

# 3. Run MCP Inspector (no env setup needed!)
npx @modelcontextprotocol/inspector uv --directory . run python -m nara_server.server
```

## Available Tools

### 1. `get_bids_by_keyword`

키워드로 최근 7일간 용역 입찰공고 및 사전규격을 검색합니다. (최대 20개 결과)

**파라미터:**
- `keyword` (필수): 검색 키워드 (예: "인공지능", "AI", "플랫폼", "시스템 구축")

**반환 정보:**

**일반 입찰공고:**
- 공고명 (bidNtceNm)
- 공고번호 (bidNtceNo)
- 수요기관 (dminsttNm)
- 예산 (bdgtAmt / presmptPrce)
- 마감일시 (bidClseDt) - 마감되지 않은 공고만
- 제안요청서 파일 (제안요청서/제안 키워드 포함 파일만 자동 필터링)

**사전규격:**
- 사전규격명 (bfSpecNm)
- 사전규격번호 (bfSpecRgstNo)
- 발주기관 (ordInsttNm)
- 배정예산 (asignBdgtAmt)
- 의견마감일시 (opnEndDt)
- 제안요청서 파일 (제안요청서/제안 키워드 포함 파일만 자동 필터링)

**예시 질문:**
```
나라장터에서 "인공지능" 키워드로 입찰공고를 검색해줘
```
```
AI 관련 정부 프로젝트 입찰 공고를 찾아줘
```

---

### 2. `recommend_bids_for_dept`

부서/팀 프로필을 기반으로 맞춤형 입찰공고를 추천합니다.

**파라미터:**
- `keyword` (필수): 검색 키워드
- `department_profile` (필수): 부서/팀 설명 (예: "UI/UX 디자인팀", "AI/ML 개발팀")

**검색 범위:**
- 최근 7일간 입찰공고 검색
- 최대 60개 결과 (일반 입찰 30개 + 사전규격 30개)

**출력 방식:**
- 사용자가 "Top 5" 또는 특정 개수를 요청하면 해당 개수만큼 추천
- "모든 관련 공고"를 요청하면 전체 목록을 적합도 순으로 표시
- 예산이 있는 항목 우선 추천
- 제안요청서/과업지시서 파일만 자동 필터링하여 표시

**예시 질문:**
```
우리 팀은 클라우드 인프라 구축 전문팀이야. "클라우드" 키워드로 우리 팀에 맞는 입찰공고 Top 5를 추천해줘
```
```
데이터베이스 마이그레이션 전문가인데, "DB" 키워드로 관련된 모든 공고를 보여줘
```

---

### 3. `analyze_bid_detail`

입찰공고 첨부파일(제안요청서)을 다운로드하고 텍스트를 추출하여 분석합니다.

**파라미터:**
- `file_url` (필수): 첨부파일 URL (검색 결과의 제안요청서 URL)
- `filename` (필수): 파일명 (검색 결과의 파일명)
- `department_profile` (선택): 부서 설명 (입력 시 전략 분석 포함)

**지원 형식:**
- **HWP**: 한글 문서 (주요 형식, langchain-teddynote HWPLoader 사용)
- **HWPX**: 한글 오피스 XML 문서
- **PDF**: 텍스트 기반 PDF (이미지 기반 PDF는 제외)
- **DOCX**: MS Word 문서
- **XLSX**: Excel 스프레드시트
- **ZIP**: 자동으로 내부 파일 선택
  - 우선순위: 제안요청서 > 과업지시서 > .hwp/.hwpx > .docx/.pdf

**예시 질문:**
```
위 공고의 첨부파일을 분석해줘. 우리 팀은 AI 개발팀이야.
```

**분석 결과:**
- **Fit Score (0-100)**: 팀과 프로젝트의 적합도
- **Core Tasks**: 팀이 수행할 핵심 업무
- **Winning Strategy**: 입찰 전략 3가지
- **Risk Factors**: 위험 요소 (기술스택, 일정, 페널티 등)

## Usage Examples

### 기본 검색

```
Q: 나라장터에서 "시스템 개발" 키워드로 입찰공고를 검색해줘

A: 🔍 **일반 입찰 공고 (Regular Bids)**
   Found 15 bid notice(s) total, 8 still open
   📅 Search period: 20260116 ~ 20260123

   ## 1. AI 기반 고객관리 시스템 개발 용역
      📌 공고번호: 20260112345-00
      🏢 수요기관: 서울시청
      💰 예산: 150,000,000원
      ⏰ 마감일시: 202601201430
      📎 제안요청서:
         - 제안요청서_AI시스템.hwp: [URL]

   ================================================================================
   📋 **사전규격 공고 (Preliminary Specifications)**
   Found 3 pre-spec(s) total, 2 still open

   ## 1. 고객관리 플랫폼 사전규격
      📌 사전규격번호: PRE20260101-01
      🏢 발주기관: 경기도청
      💰 배정예산: 80,000,000원
      ⏰ 의견마감일시: 202601251700
      📎 제안요청서:
         - 제안요청서_플랫폼.hwp: [URL]
```

### 맞춤형 추천

```
Q: 우리 팀은 React 기반 웹 프론트엔드 개발 전문팀이야. "플랫폼 구축" 키워드로 우리 팀에 맞는 입찰공고 Top 5를 추천해줘

A: 🎯 Department-Filtered Integrated Search Results

   📋 Department Profile: React 기반 웹 프론트엔드 개발 전문팀
   🔍 Keyword: 플랫폼 구축
   📊 Results:
     - Regular Bids: 22 open (out of 30 total)
     - Pre-Specs: 8 open (out of 30 total)

   **Top 5 Recommendations:**

   1. ✅ [BID] 시민참여 플랫폼 구축 (적합도 95점)
      - 예산: 200,000,000원
      - 이유: React/TypeScript 기반 웹 프론트엔드 구축 명시, UI/UX 디자인 역량 중요

   2. ✅ [PRESPEC] 공공서비스 웹포털 사전규격 (적합도 90점)
      - 예산: 150,000,000원
      - 이유: 반응형 웹 디자인 요구, 사전 의견 제출로 경쟁력 확보 가능
   ...
```

### 전략 분석

```
Q: 위 1번 공고의 첨부파일을 분석해줘

A: 📄 Bid Document Analysis

   📎 File: 제안요청서_시민참여플랫폼.hwp

   ## Strategic Analysis

   **Fit Score:** 92/100
   - React 18, TypeScript, Tailwind CSS 기술스택 요구
   - 반응형 웹 디자인 및 접근성(WCAG 2.1) 준수 필요

   **Core Tasks:**
   1. React 기반 SPA(Single Page Application) 개발
   2. 사용자 대시보드 및 관리자 콘솔 UI 구현
   3. REST API 연동 및 상태 관리 (Redux/Zustand)

   **Winning Strategy:**
   1. 포트폴리오에서 정부기관 반응형 웹 사례 강조
   2. 접근성 준수 경험 및 웹 표준 인증서 제시
   3. React 성능 최적화 기법 (Code Splitting, Lazy Loading) 강조

   **Risk Factors:**
   - ⚠️ 개발 기간 3개월로 촉박함 (일반적으로 4-5개월 소요)
   - ⚠️ 지체상금: 일 0.1% (최대 10%)
   - ✅ 기술스택은 팀 역량과 100% 일치
```

## Troubleshooting

### 1. ValueError: NARA_API_KEY environment variable is required

**원인**: API 키가 환경변수로 설정되지 않았습니다.

**해결 방법:**
- Claude Desktop 설정 파일의 `env` 섹션에 `NARA_API_KEY` 추가
- Claude Desktop 재시작

### 2. No Results Found

**원인**: 검색 결과가 없거나, 최근 7일간 해당 키워드의 진행 중인 공고가 없습니다.

**해결 방법:**
- 다른 키워드로 검색 시도 (더 일반적인 키워드 사용)
- 마감된 공고일 가능성 확인 (나라장터 웹사이트에서 직접 확인)
- 더 긴 검색 기간이 필요하면 개발자에게 문의

### 3. API Error (Code: 20 - Access Denied)

**원인**: API 키가 잘못되었거나 활용신청이 승인되지 않았습니다.

**해결 방법:**
- [공공데이터포털](https://www.data.go.kr/) > 마이페이지에서 ServiceKey 확인
- 활용신청 승인 여부 확인

### 4. HWP 파일 추출 실패

**원인**:
- DRM/암호화된 HWP 파일
- 비표준 인코딩 또는 손상된 파일
- 특수한 압축 방식 사용

**해결 방법:**
- 원본 링크에서 수동 다운로드 시도
- PDF 버전 파일이 있는지 확인
- 다른 첨부파일(DOCX, PDF 등) 사용

**참고:**
- 이 서버는 `langchain-teddynote` HWPLoader를 사용하여 대부분의 HWP 파일 처리 가능
- 추출 실패 시 `olefile` 파서로 자동 폴백

## API Information

- **데이터 출처**: 조달청 나라장터 (Korea Public Procurement Service)
- **API 서비스**: BidPublicInfoService
- **엔드포인트**:
  - 일반 입찰: `getBidPblancListInfoServcPPSSrch`
  - 사전규격: `getBfSpecRgstSttusListInfoServcPPSSrch`
- **공고 유형**: 용역 (Service) - 컨설팅, 개발, SI 프로젝트
- **검색 기간**: 최근 7일 (진행 중인 공고 비율 최적화)
- **필터링**:
  - 마감일시 기준 자동 필터링 (진행 중인 공고만 표시)
  - 제안요청서 파일 자동 선별 (제안요청서/제안 키워드 포함 파일만)

**참고:**
- 물품 공고: 엔드포인트 변경 필요 (`getBidPblancListInfoThngPPSSrch`)
- 공사 공고: 엔드포인트 변경 필요 (`getBidPblancListInfoCnstwkPPSSrch`)
- 사전규격 검색: 별도 엔드포인트 사용, 파라미터명 차이 (`bidNtceNm` vs `bfSpecNm`)

## Technical Stack

- **Python**: 3.10+
- **MCP Framework**:
  - `mcp>=1.15.0` - Model Context Protocol SDK
  - `smithery>=0.4.2` - Smithery CLI for MCP server development
- **HTTP Client**: `httpx>=0.27.0` - Async HTTP requests
- **File Extraction**:
  - `langchain-teddynote>=0.3.9` - Enhanced HWP extraction (primary, with zlib compression support)
  - `olefile>=0.47` - HWP fallback (legacy MS OLE format parser)
  - `pypdf>=4.0` - PDF text extraction
  - `python-docx>=1.1` - DOCX parsing
  - `openpyxl>=3.1` - XLSX reading
- **LLM Integration**:
  - `langchain>=0.1.0,<1.0.0` - Document loading framework
  - `langchain-core>=0.1.0,<1.0.0` - Core LangChain utilities
- **Utilities**:
  - `python-dotenv>=1.0.0` - Environment variable management

## Project Structure

```
narajangteo_mcp_server/
├── src/
│   └── nara_server/
│       ├── __init__.py          # Package initialization
│       ├── server.py             # Main MCP server with Smithery
│       └── file_extractor.py     # Multi-format file text extraction
├── pyproject.toml                # Python project metadata & dependencies
├── smithery.yaml                 # Smithery deployment configuration
├── .env                          # Environment variables (local)
├── README.md                     # This file
├── CLAUDE.md                     # Developer guide
└── LICENSE                       # MIT License
```

## Development

### Setting up development environment

```bash
# Clone repository
git clone https://github.com/Datajang/narajangteo_mcp_server.git
cd narajangteo_mcp_server

# Install in editable mode
pip install -e .

# Set environment variable
export NARA_API_KEY="your_service_key_here"  # MacOS/Linux
set NARA_API_KEY=your_service_key_here       # Windows

# Or use .env file (recommended)
echo "NARA_API_KEY=your_key" > .env
```

### Running the server

```bash
# Run directly
nara-server

# Or using Python module
python -m nara_server.server
```

### Testing with MCP Inspector

MCP Inspector provides an interactive UI for testing tools:

```bash
# Install Inspector
npm install -g @modelcontextprotocol/inspector

# Run with Inspector (automatically loads .env)
npx @modelcontextprotocol/inspector python -m nara_server.server
```

The Inspector will open http://localhost:6274 with:
- Interactive tool testing
- Real-time request/response logs
- Tool parameter validation

**Prerequisites:**
- Node.js 18+ ([Download](https://nodejs.org/))

## Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch
3. Make your changes with clear commit messages
4. Test thoroughly with real API calls
5. Submit a Pull Request

## License

MIT License - see [LICENSE](LICENSE) file for details

## Author

**Datajang** ([GitHub](https://github.com/Datajang))

## Links

- **PyPI Package**: https://pypi.org/project/nara-mcp-server/
- **GitHub Repository**: https://github.com/Datajang/narajangteo_mcp_server
- **Issues**: https://github.com/Datajang/narajangteo_mcp_server/issues
- **공공데이터포털**: https://www.data.go.kr/
- **나라장터**: https://www.g2b.go.kr/

## Acknowledgments

- 조달청 나라장터 for providing the public API
- Anthropic for the MCP protocol
- Korean government for open data initiatives
