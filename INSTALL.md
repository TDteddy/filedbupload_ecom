# 설치 가이드

## 필수 요구사항

- Python 3.8 이상
- MySQL 데이터베이스 (접근 가능한 서버)
- 데이터베이스에 필요한 테이블들이 이미 생성되어 있어야 함

## 설치 단계

### 1. 저장소 클론

```bash
git clone <repository-url>
cd filedbupload_ecom
```

### 2. 가상환경 생성 (권장)

**Linux/Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

### 3. 의존성 설치

```bash
pip install -r requirements.txt
```

### 4. 환경변수 설정

`.env.example` 파일을 복사하여 `.env` 파일을 생성:

```bash
cp .env.example .env
```

`.env` 파일을 편집하여 실제 데이터베이스 정보를 입력:

```env
DB_HOST=your_database_host
DB_USER=your_database_user
DB_PASSWORD=your_database_password
DB_NAME=sales
DB_PORT=3306
```

### 5. models.py 파일 준비

`models.py.template` 파일을 참고하여 실제 `models.py` 파일을 생성합니다.

이 파일에는 다음 두 개의 SQLAlchemy 모델이 정의되어야 합니다:

- `SKU_master`: SKU 마스터 테이블
- `coupang_1p_auto_created_vender_ID`: 쿠팡 1P 자동생성 벤더 ID 매핑 테이블

### 6. 데이터베이스 연결 테스트

```bash
python -c "from src.database import DatabaseManager; db = DatabaseManager(); print('✅ 연결 성공')"
```

### 7. 실행

처리할 파일들을 프로젝트 루트 디렉토리에 배치한 후:

```bash
python main.py
```

## 문제 해결

### ImportError: No module named 'models'

→ `models.py` 파일이 프로젝트 루트에 있는지 확인하세요.

### pymysql.err.OperationalError

→ `.env` 파일의 데이터베이스 연결 정보를 확인하세요.

### "매핑 테이블 준비 완료" 후 오류

→ 데이터베이스에 `SKU_master`와 `coupang_1p_auto_created_vender_ID` 테이블이 존재하는지 확인하세요.

## 추가 설정

### 로깅 설정

필요에 따라 로깅을 추가할 수 있습니다. `main.py`에 다음을 추가:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('upload.log'),
        logging.StreamHandler()
    ]
)
```

### 성능 최적화

대용량 파일 처리 시 메모리 사용량을 줄이려면 pandas의 청크 읽기를 고려하세요.
