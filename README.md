# E-commerce Data Upload System

이 프로젝트는 쿠팡, 네이버, 카페24 등 다양한 e-commerce 플랫폼의 판매 및 광고 데이터를 MySQL 데이터베이스에 업로드하는 자동화 시스템입니다.

## 기능

- **쿠팡 1P/2P 매출 데이터 업로드**
- **쿠팡 광고 데이터 업로드** (매출성장광고, 첫구매광고)
- **네이버 광고 및 오가닉 데이터 업로드**
- **카페24 판매 데이터 업로드**
- **SKU 마스터 매칭** 자동화
- **🤖 GPT 기반 자동 SKU 생성** (쿠팡 2P 전용)
  - 매칭 실패 시 GPT가 자동으로 상품 분석
  - 수량변경, 환불재판매, 신규상품 자동 분류
  - SKU_master 자동 업데이트
- **매칭 실패 데이터 추적**

## 프로젝트 구조

```
filedbupload_ecom/
├── config/
│   ├── __init__.py
│   └── mappings.py          # 컬럼 매핑 설정
├── src/
│   ├── __init__.py
│   ├── database.py          # DB 연결 및 세션 관리
│   ├── processors.py        # 파일 처리 로직
│   ├── utils.py             # 유틸리티 함수
│   ├── gpt_analyzer.py      # 🤖 GPT 상품 분석기
│   └── sku_generator.py     # 🤖 SKU 자동 생성기
├── models.py                # SQLAlchemy 모델 정의
├── main.py                  # 메인 실행 파일
├── .env.example             # 환경변수 예시
├── .gitignore
├── requirements.txt
├── README.md
└── README_GPT.md            # 🤖 GPT 기능 상세 가이드
```

## 설치 방법

### 1. 저장소 클론

```bash
git clone <repository-url>
cd filedbupload_ecom
```

### 2. 가상환경 생성 (선택사항)

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 또는
venv\Scripts\activate  # Windows
```

### 3. 의존성 설치

```bash
pip install -r requirements.txt
```

### 4. 환경변수 설정

`.env.example` 파일을 복사하여 `.env` 파일을 생성하고 실제 값을 입력합니다:

```bash
cp .env.example .env
```

`.env` 파일 편집:

```env
# 데이터베이스 설정
DB_HOST=your_actual_host
DB_USER=your_actual_user
DB_PASSWORD=your_actual_password
DB_NAME=sales
DB_PORT=3306

# GPT 자동 매칭 설정 (선택사항 - 쿠팡 2P만 해당)
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxx
OPENAI_MODEL=gpt-4o-mini
```

**참고**: OpenAI API 키가 없어도 기본 기능은 정상 작동합니다. GPT 자동 SKU 생성 기능만 비활성화됩니다.

### 5. 모델 파일 준비

`models.py` 파일이 프로젝트 루트에 이미 준비되어 있습니다.
- `SKU_master`: 전체 필드가 정의된 완전한 모델
- 쿠팡 2P GPT 자동 매칭에 필요한 모든 필드 포함

## 사용 방법

### 기본 실행

처리할 Excel(`.xlsx`) 또는 CSV(`.csv`) 파일들을 프로젝트 루트 디렉토리에 배치한 후:

```bash
python main.py
```

### 지원하는 파일 형식

파일명에 다음 키워드가 포함되어야 자동으로 인식됩니다:

- `쿠팡_1p_전체` - 쿠팡 1P 매출 데이터
- `쿠팡_2p_전체` - 쿠팡 2P 매출 데이터
- `쿠팡_매출성장광고` - 쿠팡 매출성장 광고 데이터
- `쿠팡_첫구매광고` - 쿠팡 첫구매 광고 데이터
- `네이버_광고_대용량` - 네이버 광고 마스터 데이터
- `네이버_광고_보고서` - 네이버 광고 보고서
- `네이버_오가닉` - 네이버 오가닉 데이터 (Excel만 지원)
- `네이버기타` - 네이버 기타 매출 데이터
- `카페24` - 카페24 판매 데이터

## 출력 파일

처리 완료 후 다음 파일들이 생성됩니다:

- `output_[원본파일명]` - ID_master가 매핑된 전체 데이터
- `unmatched_[원본파일명]` - SKU 매핑에 실패한 데이터

## 데이터베이스 테이블

시스템은 다음 테이블들에 데이터를 저장합니다:

- `sales_report_coupang_1p` - 쿠팡 1P 매출
- `sales_report_coupang_2p` - 쿠팡 2P 매출
- `sales_report_coupang_2p_all` - 쿠팡 2P 전체 원본 (매칭 실패 포함)
- `ad_report_coupang_by_growth` - 쿠팡 매출성장광고
- `ad_report_coupang_by_firstbuy` - 쿠팡 첫구매광고
- `ad_ID_daily_update_naver` - 네이버 광고 마스터
- `ad_report_naver_summary` - 네이버 광고 보고서
- `keyword_click_report_naver_organic` - 네이버 오가닉 클릭
- `keyword_purchase_report_naver_organic` - 네이버 오가닉 구매
- `sales_report_naver_etc` - 네이버 기타 매출
- `sales_report_cafe24` - 카페24 판매

## 🤖 GPT 자동 SKU 생성 (쿠팡 2P)

쿠팡 2P 매칭 실패 시 GPT가 자동으로 상품을 분석하여 SKU_master에 추가합니다.

**상세 가이드**: [README_GPT.md](README_GPT.md) 참고

**주요 기능**:
- 수량변경 자동생성 감지 (예: 500ml → 1L)
- 환불/재판매 상품 감지
- 신규 상품 자동 등록
- ID_master 자동 생성 규칙:
  - 수량변경: `42-1`, `42-2`, `42-3`...
  - 환불재판매: `15-A`, `15-B`, `15-C`...
  - 신규상품: `201`, `202`, `203`...

## 주의사항

1. **데이터 백업**: 처리 전 원본 데이터를 백업하세요.
2. **날짜 형식**: 일부 파일은 날짜가 없을 수 있으며, 실행 중 입력을 요구합니다.
3. **매칭 실패**: `unmatched_` 파일을 확인하여 매칭되지 않은 SKU를 수동으로 처리하세요.
4. **민감정보**: `.env` 파일은 절대 git에 커밋하지 마세요.

## 문제 해결

### DB 연결 오류

```
pymysql.err.OperationalError: (2003, "Can't connect to MySQL server")
```

→ `.env` 파일의 DB 연결 정보를 확인하세요.

### 매핑 실패

→ 쿠팡 2P의 경우 GPT가 자동으로 처리합니다. 다른 플랫폼은 `SKU_master` 테이블에 해당 SKU가 존재하는지 확인하세요.

## 라이선스

MIT License

## 기여

이슈 및 풀 리퀘스트를 환영합니다.
