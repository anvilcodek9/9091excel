# Naver Smart Store - Logen Delivery Integration

Python-based automation tool that fetches order data from Naver Smart Store and generates Excel files in Logen delivery service's bulk shipping format.

## Features

- Fetches orders from Naver Commerce API with payment status "PAYED" and shipping status "READY"
- Transforms Naver order data to Logen delivery format
- Generates dated Excel files ready for upload to Logen's bulk shipping system
- Comprehensive error handling with retry logic for API failures
- Validates required fields before processing

## Installation

### Prerequisites

- Python 3.9 or higher
- pip package manager

### Install Dependencies

```bash
pip install -r requirements.txt
```

Required packages:
- `requests` - HTTP client for Naver Commerce API
- `openpyxl` - Excel file generation
- `bcrypt` - 네이버 커머스 API 토큰 발급 시 전자서명 생성
- `pytest` - Testing framework
- `hypothesis` - Property-based testing library

## Configuration

### Access Token (인증)

다음 세 가지 방식 중 하나로 인증할 수 있습니다. 우선순위는 **1 → 2 → 3** 입니다.

**방법 1: 액세스 토큰 직접 사용**

- 환경 변수: `NAVER_ACCESS_TOKEN=your_access_token_here`
- 또는 함수 인자: `generate_logen_shipping_file(access_token="...")`

**방법 2: 토큰 자동 발급 (Client ID / Secret)**

- 환경 변수로 **애플리케이션 ID**와 **시크릿**만 설정하면, 프로그램이 네이버 커머스 API 규격에 따라 토큰을 자동 발급합니다.
- [커머스API 센터](https://apicenter.commerce.naver.com)에서 애플리케이션을 생성한 뒤 발급받은 값을 사용하세요.

```bash
export NAVER_CLIENT_ID="your_application_id"
export NAVER_CLIENT_SECRET="your_client_secret"
```

- 토큰 유효 시간은 3시간이며, 실행 시마다 필요하면 새 토큰을 발급합니다.

**방법 3: 함수 인자로 토큰 전달**

- 호출 시 `access_token` 인자로 전달 (위 사용 예 참고).

## Usage

### Basic Usage

```python
from src.main import generate_logen_shipping_file

# Using environment variable for access token
file_path = generate_logen_shipping_file()
print(f"Excel file generated: {file_path}")
```

### With Access Token Parameter

```python
from src.main import generate_logen_shipping_file

# Passing access token directly
access_token = "your_access_token_here"
file_path = generate_logen_shipping_file(access_token=access_token)
print(f"Excel file generated: {file_path}")
```

### Error Handling

```python
from src.main import generate_logen_shipping_file
from src.exceptions import NaverAPIError, DataTransformError, ExcelGenerationError

try:
    file_path = generate_logen_shipping_file()
    print(f"Success! File created: {file_path}")
except NaverAPIError as e:
    print(f"API Error: {e}")
except DataTransformError as e:
    print(f"Data Transformation Error: {e}")
except ExcelGenerationError as e:
    print(f"Excel Generation Error: {e}")
```

## exe로 빌드 및 실행

Python 없이 단일 exe로 배포할 수 있습니다. **exe는 Windows에서만 실행되며, 빌드도 Windows에서 진행하는 것을 권장합니다.**

### exe 빌드 (Windows)

```bash
# 빌드용 의존성 설치
pip install -r requirements-build.txt

# 프로젝트 루트에서 빌드
pyinstaller logen_excel.spec
```

빌드가 끝나면 `dist/LogenExcel.exe` 파일이 생성됩니다.

### exe 실행

1. **인증 설정**  
   exe 실행 전 다음 중 하나를 설정합니다.
   - **액세스 토큰 직접 사용:**  
     `set NAVER_ACCESS_TOKEN=your_access_token_here`
   - **토큰 자동 발급:**  
     `set NAVER_CLIENT_ID=your_application_id`  
     `set NAVER_CLIENT_SECRET=your_client_secret`  
   - 또는 [시스템 속성] → [고급] → [환경 변수]에서 사용자/시스템 변수로 등록

2. **실행**  
   `LogenExcel.exe`를 더블클릭하거나, exe가 있는 폴더를 현재 디렉터리로 연 뒤:
   ```cmd
   LogenExcel.exe
   ```

3. **결과**  
   성공 시 콘솔에 생성된 Excel 파일 경로가 출력되고, exe가 있는 디렉터리(또는 작업 디렉터리)에 `로젠발송양식_YYYYMMDD.xlsx` 파일이 생성됩니다.  
   토큰 미설정·API 오류 등이 있으면 콘솔에 오류 메시지가 출력됩니다.

## Output

The system generates an Excel file with the following format:

**Filename:** `로젠발송양식_YYYYMMDD.xlsx` (where YYYYMMDD is the current date)

**Columns:**
- Column A: 받는사람 (Receiver Name)
- Column B: 주소 (Full Address)
- Column C: 전화번호 (Phone Number)
- Column D: 상품명 (Product Name)
- Column E: 배송메모 (Delivery Memo)

## Testing

### Run All Tests

```bash
pytest
```

### Run Tests with Verbose Output

```bash
pytest -v
```

### Run Tests with Coverage Report

```bash
# Install pytest-cov if not already installed
pip install pytest-cov

# Run tests with coverage
pytest --cov=src --cov-report=term-missing
```

### Run Tests with Branch Coverage

```bash
pytest --cov=src --cov-branch --cov-report=term
```

### Run Specific Test Files

```bash
# Test API client
pytest tests/test_api_client.py

# Test transformer
pytest tests/test_transformer.py

# Test Excel generator
pytest tests/test_excel_generator.py
```

## Project Structure

```
.
├── run.py                     # exe 빌드용 엔트리 포인트
├── logen_excel.spec           # PyInstaller 빌드 설정
├── requirements.txt
├── requirements-build.txt     # exe 빌드 시 사용 (pyinstaller 포함)
├── src/
│   ├── __init__.py
│   ├── api_client.py          # Naver Commerce API client
│   ├── transformer.py         # Data transformation logic
│   ├── excel_generator.py     # Excel file generation
│   ├── utils.py               # Utility functions
│   ├── models.py              # Data models
│   ├── exceptions.py          # Custom exceptions
│   ├── platform_check.py      # Windows 전용 실행 체크
│   └── main.py                # Main integration function
├── tests/
│   ├── __init__.py
│   ├── test_api_client.py
│   ├── test_transformer.py
│   ├── test_excel_generator.py
│   ├── test_utils.py
│   ├── test_main.py
│   └── test_platform_check.py
└── README.md
```

## Components

### API Client (`src/api_client.py`)

Handles communication with Naver Commerce API:
- OAuth2 authentication using access token
- Automatic retry with exponential backoff for transient failures
- Filters orders by payment and shipping status

### Data Transformer (`src/transformer.py`)

Transforms Naver order data to Logen format:
- Maps Naver fields to Logen columns
- Combines base address and detailed address
- Validates required fields
- Handles missing optional fields

### Excel Generator (`src/excel_generator.py`)

Creates Excel files in Logen's format:
- Generates dated filenames
- Creates proper header row
- Formats data according to Logen specifications

## Error Handling

The system includes three custom exception types:

### NaverAPIError

Raised when API requests fail:
- Authentication failures (401)
- Network connectivity issues
- Server errors (5xx)
- Rate limiting (429)

### DataTransformError

Raised when data transformation fails:
- Missing required fields
- Invalid data types
- Malformed data

### ExcelGenerationError

Raised when Excel file creation fails:
- File system permission issues
- Disk space problems
- Invalid file paths

## API Retry Logic

The system implements exponential backoff for transient API failures:
- Maximum 3 retry attempts
- Initial delay: 1 second
- Exponential multiplier: 2x
- Retries on: Network errors, 5xx server errors

## Requirements

For detailed requirements and acceptance criteria, see:
- `.kiro/specs/naver-smartstore-logen-integration/requirements.md`
- `.kiro/specs/naver-smartstore-logen-integration/design.md`

## License

This project is proprietary software for internal use.
