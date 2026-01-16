# Nara MCP Server (나라장터 입찰공고 검색)

MCP server for searching Korean government procurement bid notices from G2B (나라장터 - Nara Jangteo).

## Features

- 🔍 **키워드 검색**: 최근 7일간 용역 입찰공고를 키워드로 검색
- 📅 **자동 필터링**: 마감되지 않은 공고만 자동 필터링
- 📎 **파일 추출**: 제안요청서(RFP) 자동 다운로드 및 텍스트 추출
- 🏢 **맞춤형 추천**: 부서 프로필 기반 Top 5 입찰공고 추천
- 📄 **다형식 지원**: HWP, HWPX, PDF, DOCX, XLSX, ZIP 파일 자동 처리
- 🎯 **전략 분석**: 첨부파일 기반 입찰 전략 제안

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

### Option 1: From Source (권장)

```bash
git clone https://github.com/Datajang/narajangteo_mcp_server.git
cd narajangteo_mcp_server
pip install -r requirements.txt
```

### Option 2: From PyPI (향후 제공 예정)

```bash
pip install nara-mcp-server
```

## Configuration

### Claude Desktop

Claude Desktop의 설정 파일을 수정하여 MCP 서버를 연결합니다.

**설정 파일 위치:**
- **MacOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%/Claude/claude_desktop_config.json`

**설정 예시:**

```json
{
  "mcpServers": {
    "nara-jangteo": {
      "command": "python",
      "args": ["C:\\absolute\\path\\to\\naraMcp\\server.py"],
      "env": {
        "NARA_API_KEY": "여기에_발급받은_ServiceKey_입력"
      }
    }
  }
}
```

**중요 사항:**
- `args`의 경로는 **절대 경로**로 지정
- Windows 경로는 `\\`로 구분 (예: `C:\\Users\\...`)
- `NARA_API_KEY`에 발급받은 ServiceKey 입력

### Other MCP Clients

Continue, Cline 등 다른 MCP 클라이언트에서도 동일한 방식으로 환경변수 설정:

```json
{
  "env": {
    "NARA_API_KEY": "your_service_key_here"
  }
}
```

## Available Tools

### 1. `get_bids_by_keyword`

키워드로 최근 7일간 용역 입찰공고를 검색합니다.

**파라미터:**
- `keyword` (필수): 검색 키워드 (예: "인공지능", "AI", "플랫폼", "시스템 구축")

**반환 정보:**
- 공고명 (bidNtceNm)
- 공고번호 (bidNtceNo)
- 수요기관 (dminsttNm)
- 마감일시 (bidClseDt) - 마감되지 않은 공고만
- 제안요청서 링크 (ntceSpecDocUrl1)

**예시 질문:**
```
나라장터에서 "인공지능" 키워드로 입찰공고를 검색해줘
```
```
AI 관련 정부 프로젝트 입찰 공고를 찾아줘
```

---

### 2. `recommend_bids_for_dept`

부서/팀 프로필을 기반으로 맞춤형 입찰공고를 추천합니다 (최대 30개 검색 후 Top 5 선정).

**파라미터:**
- `keyword` (필수): 검색 키워드
- `department_profile` (필수): 부서/팀 설명 (예: "UI/UX 디자인팀", "AI/ML 개발팀")

**예시 질문:**
```
우리 팀은 클라우드 인프라 구축 전문팀이야. "클라우드" 키워드로 우리 팀에 맞는 입찰공고 추천해줘
```
```
데이터베이스 마이그레이션 전문가인데, "DB" 키워드로 적합한 입찰공고를 찾아줘
```

---

### 3. `analyze_bid_detail`

입찰공고 첨부파일(제안요청서)을 다운로드하고 텍스트를 추출하여 분석합니다.

**파라미터:**
- `file_url` (필수): 첨부파일 URL (검색 결과의 ntceSpecDocUrl1)
- `filename` (필수): 파일명 (검색 결과의 ntceSpecFileNm1)
- `department_profile` (선택): 부서 설명 (입력 시 전략 분석 포함)

**지원 형식:**
- **HWP/HWPX**: 한글 문서 (주요 형식)
- **PDF**: 이미지 기반 PDF는 제외
- **DOCX**: MS Word 문서
- **XLSX**: Excel 스프레드시트
- **ZIP**: 자동으로 내부 파일 선택 (제안요청서 우선)

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

A: 🔍 Found 15 bid notice(s) total, 8 still open for keyword: '시스템 개발'
   📅 Search period: 20260109 ~ 20260116

   ## 1. AI 기반 고객관리 시스템 개발 용역
      📌 공고번호: 20260112345-00
      🏢 수요기관: 서울시청
      ⏰ 마감일시: 202601201430
      📎 제안요청서: [다운로드 링크]
```

### 맞춤형 추천

```
Q: 우리 팀은 React 기반 웹 프론트엔드 개발 전문팀이야. "플랫폼 구축" 키워드로 우리 팀에 맞는 입찰공고 Top 5를 추천해줘

A: 🎯 Department-Filtered Bid Search Results

   📋 Department Profile: React 기반 웹 프론트엔드 개발 전문팀
   🔍 Keyword: 플랫폼 구축
   📊 Total Open Bids: 22 (out of 30 total)

   **Top 5 Recommendations:**

   1. ✅ 시민참여 플랫폼 구축 (적합도 95점)
      - React/TypeScript 기반 웹 프론트엔드 구축 명시
      - UI/UX 디자인 역량 중요
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

### 2. API Error (Code: 03 - No Data)

**원인**: 검색 결과가 없거나, 최근 7일간 해당 키워드의 공고가 없습니다.

**해결 방법:**
- 다른 키워드로 검색 시도
- 검색 기간을 확장하고 싶다면 개발자에게 문의

### 3. API Error (Code: 20 - Access Denied)

**원인**: API 키가 잘못되었거나 활용신청이 승인되지 않았습니다.

**해결 방법:**
- [공공데이터포털](https://www.data.go.kr/) > 마이페이지에서 ServiceKey 확인
- 활용신청 승인 여부 확인

### 4. HWP 파일 추출 실패

**원인**: DRM/암호화된 HWP 파일이거나 비표준 인코딩입니다.

**해결 방법:**
- 원본 링크에서 수동 다운로드 시도
- PDF 버전 파일이 있는지 확인

## API Information

- **데이터 출처**: 조달청 나라장터 (Korea Public Procurement Service)
- **API 서비스**: BidPublicInfoService
- **엔드포인트**: `getBidPblancListInfoServcPPSSrch`
- **공고 유형**: 용역 (Service) - 컨설팅, 개발, SI 프로젝트
- **검색 기간**: 최근 7일 (마감되지 않은 공고 비율 최적화)
- **필터링**: 마감일시 기준 자동 필터링

**참고:**
- 물품 공고: 엔드포인트 변경 필요 (`getBidPblancListInfoThngPPSSrch`)
- 공사 공고: 엔드포인트 변경 필요 (`getBidPblancListInfoCnstwkPPSSrch`)

## Technical Stack

- **Python**: 3.10+
- **MCP SDK**: `mcp[cli]` - Model Context Protocol server framework
- **HTTP Client**: `httpx` - Async HTTP requests
- **File Extraction**:
  - `olefile` - HWP (MS OLE format)
  - `pypdf` - PDF text extraction
  - `python-docx` - DOCX parsing
  - `openpyxl` - XLSX reading

## Project Structure

```
naraMcp/
├── server.py              # Main MCP server
├── file_extractor.py      # Multi-format file text extraction
├── pyproject.toml         # Python project metadata
├── requirements.txt       # Python dependencies
├── README.md              # This file
├── CLAUDE.md              # Developer guide
├── SMITHERY_GUIDE.md      # Publishing guide
└── LICENSE                # MIT License
```

## Development

### Local Testing

```bash
# Set environment variable
export NARA_API_KEY="your_service_key_here"  # MacOS/Linux
set NARA_API_KEY=your_service_key_here       # Windows

# Run server
python server.py
```

### Testing with MCP Inspector

```bash
# Install MCP Inspector
npm install -g @modelcontextprotocol/inspector

# Run with inspector
mcp-inspector python server.py
```

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

- **Repository**: https://github.com/Datajang/nara-mcp-server
- **Issues**: https://github.com/Datajang/nara-mcp-server/issues
- **공공데이터포털**: https://www.data.go.kr/
- **나라장터**: https://www.g2b.go.kr/

## Acknowledgments

- 조달청 나라장터 for providing the public API
- Anthropic for the MCP protocol
- Korean government for open data initiatives
