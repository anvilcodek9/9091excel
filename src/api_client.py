"""Naver Commerce API client for fetching order data."""

import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

import requests

from .exceptions import NaverAPIError


class NaverCommerceClient:
    """
    Client for interacting with Naver Commerce API.
    
    This client handles authentication, request retries with exponential backoff,
    and error handling for the Naver Commerce API.
    
    Attributes:
        access_token: OAuth2 access token for API authentication
        base_url: Base URL for Naver Commerce API
        max_retries: Maximum number of retry attempts for failed requests
        initial_delay: Initial delay in seconds for exponential backoff
        backoff_multiplier: Multiplier for exponential backoff delay
    """
    
    def __init__(self, access_token: str):
        """
        Initialize the Naver Commerce API client.
        
        Args:
            access_token: OAuth2 access token for authentication
        """
        self.access_token = access_token
        self.base_url = "https://api.commerce.naver.com/external/v1"
        self.max_retries = 3
        self.initial_delay = 1
        self.backoff_multiplier = 2
    
    def fetch_orders(
        self,
        payment_status: str = "PAYED",
        shipping_status: Optional[str] = "READY",
        last_hours: int = 24,
        from_iso: Optional[str] = None,
        to_iso: Optional[str] = None,
        _split_long_range: bool = True,
    ) -> List[Dict]:
        """
        Fetch orders from Naver Commerce API with specified filters.
        
        This method retrieves orders filtered by payment status and shipping status.
        It implements retry logic with exponential backoff for transient failures
        (5xx errors) and raises NaverAPIError for authentication failures (401)
        and other errors.
        
        Args:
            payment_status: Payment status filter (default: "PAYED")
            shipping_status: Shipping status filter (default: "READY"). None 또는 "" 이면 미전송(전체 배송상태 조회, 테스트용)
            last_hours: 조회 기간(시간). from_iso/to_iso 미지정 시 사용. API 제한으로 최대 23.
            from_iso: 테스트용. 조회 시작 시각 ISO-8601 (지정 시 last_hours 무시)
            to_iso: 테스트용. 조회 종료 시각 ISO-8601 (from_iso와 함께 사용, 최대 24시간 차이)
            _split_long_range: 내부용 플래그. True일 때 from/to 구간이 24시간을 초과하면 자동으로 23시간 단위로 쪼개어 여러 번 조회합니다.
        
        Returns:
            List of order dictionaries from the API response
        
        Raises:
            NaverAPIError: When API request fails due to authentication,
                          network errors, or server errors after all retries
        """
        # 긴 기간(>24시간)을 사용자 편의상 자동으로 23시간 단위로 나누어 조회
        if from_iso and to_iso and _split_long_range:
            try:
                # 'Z' → '+00:00' 으로 치환하여 표준 ISO-8601로 파싱
                start_dt = datetime.fromisoformat(from_iso.replace("Z", "+00:00"))
                end_dt = datetime.fromisoformat(to_iso.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                # 형식이 잘못된 경우에는 기존 로직에 맡기고, 서버에서 에러를 반환하도록 둔다.
                start_dt = end_dt = None

            if start_dt and end_dt and end_dt > start_dt:
                total_span = end_dt - start_dt
                max_api_span = timedelta(hours=24)
                # 네이버 API 제약: from~to 최대 24시간.
                # 사용자가 더 긴 기간을 선택하면 23시간 단위로 자동 분할 조회.
                if total_span > max_api_span:
                    all_orders: List[Dict] = []
                    chunk = timedelta(hours=23)
                    epsilon = timedelta(milliseconds=1)
                    current_start = start_dt

                    while current_start < end_dt:
                        current_end = min(current_start + chunk, end_dt)
                        sub_from = current_start.isoformat(timespec="milliseconds")
                        sub_to = current_end.isoformat(timespec="milliseconds")
                        partial = self.fetch_orders(
                            payment_status=payment_status,
                            shipping_status=shipping_status,
                            last_hours=last_hours,
                            from_iso=sub_from,
                            to_iso=sub_to,
                            _split_long_range=False,
                        )
                        all_orders.extend(partial)
                        # 다음 구간은 1ms 뒤부터 시작하여 중복 최소화
                        current_start = current_end + epsilon

                    return all_orders

        # 주문 조회 API 경로 업데이트:
        # (구) /v1/product-orders/query -> (신) /v1/pay-order/seller/product-orders
        url = f"{self.base_url}/pay-order/seller/product-orders"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        if from_iso and to_iso:
            from_str, to_str = from_iso, to_iso
        else:
            last_hours = min(23, max(1, int(last_hours)))
            now_kst = datetime.now(timezone(timedelta(hours=9)))
            from_kst = now_kst - timedelta(hours=last_hours)
            from_str = from_kst.isoformat(timespec="milliseconds")
            to_str = now_kst.isoformat(timespec="milliseconds")
        params = {
            "rangeType": "PAYED_DATETIME",
            "from": from_str,
            "to": to_str,
            "paymentStatus": payment_status,
        }
        if shipping_status:
            params["shippingStatus"] = shipping_status
        
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                response = requests.get(url, headers=headers, params=params, timeout=30)
                
                # Handle authentication failure immediately (no retry)
                if response.status_code == 401:
                    raise NaverAPIError(
                        "Authentication failed: Invalid or expired access token",
                        status_code=401,
                        response_body=response.text
                    )
                
                # Handle server errors with retry
                if response.status_code >= 500:
                    last_error = NaverAPIError(
                        f"Server error occurred (attempt {attempt + 1}/{self.max_retries})",
                        status_code=response.status_code,
                        response_body=response.text
                    )
                    
                    # If not the last attempt, wait and retry
                    if attempt < self.max_retries - 1:
                        delay = self.initial_delay * (self.backoff_multiplier ** attempt)
                        time.sleep(delay)
                        continue
                    else:
                        # Last attempt failed, raise the error
                        raise last_error
                
                # Handle other HTTP errors
                if not response.ok:
                    raise NaverAPIError(
                        f"API request failed with status {response.status_code}",
                        status_code=response.status_code,
                        response_body=response.text
                    )
                
                # Success - parse and return the response
                data = response.json()
                
                # 조건형 상품 주문 상세 내역 조회 API 응답 형태:
                # (1) data: [ { "order": {...}, "productOrder": {...} } ]
                # (2) data: { "contents": [ { "content": { "order": {...}, "productOrder": {...} } } ] }
                raw_list = None
                if isinstance(data, dict) and "data" in data:
                    inner = data["data"]
                    if isinstance(inner, list):
                        raw_list = inner
                    elif isinstance(inner, dict):
                        raw_list = inner.get("contents") or inner.get("orders") or inner.get("productOrders")
                        if raw_list is None and "content" in inner:
                            raw_list = inner["content"] if isinstance(inner["content"], list) else [inner["content"]]
                        if raw_list is None:
                            raw_list = []
                elif isinstance(data, list):
                    raw_list = data
                else:
                    raw_list = []

                if not raw_list:
                    return []

                # API 스키마에 맞게 평탄화: order + productOrder + shippingAddress -> 한 건당 하나의 flat dict
                # contents[] 항목은 { "content": { "order", "productOrder" } } 형태일 수 있음
                orders = []
                for item in raw_list:
                    if not isinstance(item, dict):
                        continue
                    block = item.get("content") if isinstance(item.get("content"), dict) else item
                    order_block = block.get("order") or {}
                    product_order = block.get("productOrder") or {}

                    if product_order:
                        # 실제 API 응답: order + productOrder + shippingAddress
                        shipping = product_order.get("shippingAddress") or {}
                        order_id = order_block.get("orderId") or product_order.get("productOrderId") or ""
                        receiver_name = shipping.get("name") or ""
                        base_address = shipping.get("baseAddress") or ""
                        detailed_address = shipping.get("detailedAddress") or ""
                        receiver_tel = shipping.get("tel1") or shipping.get("tel2") or ""
                        product_name = product_order.get("productName") or ""
                        delivery_memo = product_order.get("shippingMemo") or ""
                        orders.append({
                            "order_id": order_id,
                            "receiverName": receiver_name,
                            "baseAddress": base_address,
                            "detailedAddress": detailed_address,
                            "receiverTel1": receiver_tel,
                            "productName": product_name,
                            "deliveryMemo": delivery_memo,
                        })
                    else:
                        # 이미 flat 형태(테스트/레거시): orderId -> order_id, 나머지 키 그대로
                        flat = dict(item)
                        if "orderId" in flat and "order_id" not in flat:
                            flat["order_id"] = flat.get("orderId", "")
                        orders.append(flat)
                return orders
            
            except requests.exceptions.RequestException as e:
                # Network errors - retry with exponential backoff
                last_error = NaverAPIError(
                    f"Network error occurred (attempt {attempt + 1}/{self.max_retries}): {str(e)}",
                    status_code=None,
                    response_body=None
                )
                
                # If not the last attempt, wait and retry
                if attempt < self.max_retries - 1:
                    delay = self.initial_delay * (self.backoff_multiplier ** attempt)
                    time.sleep(delay)
                    continue
                else:
                    # Last attempt failed, raise the error
                    raise last_error
        
        # This should not be reached, but just in case
        if last_error:
            raise last_error
        else:
            raise NaverAPIError("Unknown error occurred during API request")
