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


def generate_logen_shipping_file(access_token: Optional[str] = None) -> str:
    """
    Fetches orders from Naver Smart Store and generates Logen shipping Excel file.
    
    This function orchestrates the entire workflow:
    1. Obtains access token (parameter → NAVER_ACCESS_TOKEN → NAVER_CLIENT_ID+NAVER_CLIENT_SECRET 자동 발급)
    2. Fetches orders from Naver Commerce API
    3. Transforms order data to Logen format
    4. Generates Excel file with current date in filename
    
    Args:
        access_token: OAuth2 access token for Naver Commerce API.
                     If not provided, uses NAVER_ACCESS_TOKEN, or auto-issues via NAVER_CLIENT_ID + NAVER_CLIENT_SECRET.
        
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
    print(access_token)
    
    # 조회 기간(시간). 환경 변수 NAVER_ORDER_LAST_HOURS 없으면 기본 24시간. (네이버 API 제한으로 최대 24시간)
    last_hours = 24
    try:
        env_hours = os.environ.get("NAVER_ORDER_LAST_HOURS")
        if env_hours is not None and env_hours != "":
            last_hours = int(env_hours)
    except ValueError:
        last_hours = 24

    # 조회 구간: NAVER_ORDER_FROM/TO 미설정 시 최신 23시간 내(api_client에서 last_hours 사용)
    from_iso = os.environ.get("NAVER_ORDER_FROM", "").strip() or None
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
    
    # Generate output filename using date formatting utility
    filename = generate_logen_filename()
    
    # Call LogenExcelGenerator.generate_excel to create Excel file
    output_path = LogenExcelGenerator.generate_excel(transformed_orders, filename)
    
    # Return path to generated Excel file
    return output_path
