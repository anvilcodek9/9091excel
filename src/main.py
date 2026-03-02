"""Main function for Naver Smart Store - Logen Delivery Integration."""

import os
from typing import Optional

from .api_client import NaverCommerceClient
from .auth import resolve_access_token
from .transformer import OrderTransformer
from .excel_generator import LogenExcelGenerator
from .utils import generate_logen_filename
from .exceptions import NaverAPIError, DataTransformError, ExcelGenerationError
from .platform_check import ensure_windows_platform


def generate_logen_shipping_file(
    access_token: Optional[str] = None,
    from_iso: Optional[str] = None,
    to_iso: Optional[str] = None,
    last_hours: Optional[int] = None,
) -> str:
    """
    Fetches orders from Naver Smart Store and generates Logen shipping Excel file.
    
    This function orchestrates the entire workflow:
    1. Obtains access token (parameter → NAVER_ACCESS_TOKEN → NAVER_CLIENT_ID+NAVER_CLIENT_SECRET 자동 발급)
    2. Fetches orders from Naver Commerce API (지정한 기간 기준)
    3. Transforms order data to Logen format
    4. Generates Excel file; 파일명에 조회 기간이 반영됨 (기간 지정 시)
    
    Args:
        access_token: OAuth2 access token for Naver Commerce API.
                     If not provided, uses NAVER_ACCESS_TOKEN, or auto-issues via NAVER_CLIENT_ID + NAVER_CLIENT_SECRET.
        from_iso: 조회 시작 시각 ISO-8601. 지정 시 to_iso와 함께 사용 (네이버 API는 최대 24시간 구간).
        to_iso: 조회 종료 시각 ISO-8601. from_iso와 함께 사용.
        last_hours: 조회 기간(시간). from_iso/to_iso 미지정 시 사용. 기본 24, 최대 23.
        
    Returns:
        str: Path to generated Excel file
        
    Raises:
        NaverAPIError: When API request fails
        DataTransformError: When data transformation fails
        ExcelGenerationError: When Excel file creation fails
        ValueError: When access token is not available and auto-issue is not possible
    """
    ensure_windows_platform()

    # 토큰 결정: 인자 → 환경 변수(NAVER_ACCESS_TOKEN) → client_id/secret으로 자동 발급
    access_token = resolve_access_token(
        access_token=access_token or os.environ.get("NAVER_ACCESS_TOKEN"),
        client_id=os.environ.get("NAVER_CLIENT_ID"),
        client_secret=os.environ.get("NAVER_CLIENT_SECRET"),
    )
    
    # Instantiate NaverCommerceClient with access_token
    client = NaverCommerceClient(access_token)
    
    # 조회 기간: 인자 우선, 없으면 환경 변수, 최종 기본값 24시간
    if last_hours is None:
        last_hours = 24
        try:
            env_hours = os.environ.get("NAVER_ORDER_LAST_HOURS")
            if env_hours is not None and env_hours != "":
                last_hours = int(env_hours)
        except ValueError:
            last_hours = 24

    # 조회 구간: 인자로 from/to 지정 시 그대로 사용, 없으면 환경 변수
    if from_iso is None:
        from_iso = os.environ.get("NAVER_ORDER_FROM", "").strip() or None
    if to_iso is None:
        to_iso = os.environ.get("NAVER_ORDER_TO", "").strip() or None
    # 배송상태: NAVER_INCLUDE_ALL_SHIPPING=1 이면 전체, 아니면 배송준비중(READY)만
    shipping_status = "READY"
    if os.environ.get("NAVER_INCLUDE_ALL_SHIPPING", "").strip().upper() in ("1", "TRUE", "YES"):
        shipping_status = None

    # Call fetch_orders to get order data
    orders = client.fetch_orders(
        last_hours=last_hours,
        shipping_status=shipping_status,
        from_iso=from_iso,
        to_iso=to_iso,
    )
    print(f"주문 조회: {len(orders)}건")

    # Call OrderTransformer.transform_to_logen_format to transform data
    transformed_orders = OrderTransformer.transform_to_logen_format(orders)
    
    # Generate output filename: 지정한 기간이 있으면 파일명에 반영
    filename = generate_logen_filename(from_iso=from_iso, to_iso=to_iso)
    
    # Call LogenExcelGenerator.generate_excel to create Excel file
    output_path = LogenExcelGenerator.generate_excel(transformed_orders, filename)
    
    # Return path to generated Excel file
    return output_path
