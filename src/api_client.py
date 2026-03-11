"""Naver Commerce API client for fetching order data."""

import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

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

    @staticmethod
    def _extract_raw_list(data: Any) -> List[Dict[str, Any]]:
        """API 응답에서 주문 항목 리스트를 추출."""
        raw_list: Any = None
        if isinstance(data, dict) and "data" in data:
            inner = data["data"]
            if isinstance(inner, list):
                raw_list = inner
            elif isinstance(inner, dict):
                raw_list = inner.get("contents") or inner.get("orders") or inner.get("productOrders")
                if raw_list is None and "content" in inner:
                    raw_content = inner["content"]
                    raw_list = raw_content if isinstance(raw_content, list) else [raw_content]
        elif isinstance(data, list):
            raw_list = data

        if not isinstance(raw_list, list):
            return []
        return [item for item in raw_list if isinstance(item, dict)]

    @staticmethod
    def _extract_product_order_id(item: Dict[str, Any]) -> str:
        """raw item에서 productOrderId를 최대한 안전하게 추출."""
        block = item.get("content") if isinstance(item.get("content"), dict) else item
        product_order = block.get("productOrder") if isinstance(block.get("productOrder"), dict) else {}
        return str(
            product_order.get("productOrderId")
            or block.get("productOrderId")
            or item.get("productOrderId")
            or ""
        ).strip()

    def _fetch_order_details_by_ids(self, product_order_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        productOrderId 리스트로 상세조회 후, id -> {order, productOrder} 맵을 반환.
        실패 시 빈 dict 반환(호출부에서 기존 응답으로 폴백).
        """
        unique_ids = []
        seen = set()
        for pid in product_order_ids:
            val = str(pid or "").strip()
            if val and val not in seen:
                seen.add(val)
                unique_ids.append(val)
        if not unique_ids:
            return {}

        url = f"{self.base_url}/pay-order/seller/product-orders/query"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        detail_map: Dict[str, Dict[str, Any]] = {}

        # API 한 번에 너무 많은 ID를 보내지 않도록 청크 조회
        chunk_size = 100
        for i in range(0, len(unique_ids), chunk_size):
            chunk_ids = unique_ids[i : i + chunk_size]
            payload = {"productOrderIds": chunk_ids}

            last_error: Optional[Exception] = None
            for attempt in range(self.max_retries):
                try:
                    response = requests.post(url, headers=headers, json=payload, timeout=30)
                    if response.status_code == 401:
                        raise NaverAPIError(
                            "Authentication failed: Invalid or expired access token",
                            status_code=401,
                            response_body=response.text,
                        )
                    if response.status_code >= 500:
                        if attempt < self.max_retries - 1:
                            delay = self.initial_delay * (self.backoff_multiplier ** attempt)
                            time.sleep(delay)
                            continue
                        break
                    if not response.ok:
                        break

                    detail_items = self._extract_raw_list(response.json())
                    for item in detail_items:
                        block = item.get("content") if isinstance(item.get("content"), dict) else item
                        order_block = block.get("order") if isinstance(block.get("order"), dict) else {}
                        product_order = block.get("productOrder") if isinstance(block.get("productOrder"), dict) else {}
                        product_order_id = str(
                            product_order.get("productOrderId")
                            or block.get("productOrderId")
                            or ""
                        ).strip()
                        if not product_order_id:
                            continue
                        detail_map[product_order_id] = {
                            "order": order_block,
                            "productOrder": product_order,
                        }
                    break
                except requests.exceptions.RequestException as e:
                    last_error = e
                    if attempt < self.max_retries - 1:
                        delay = self.initial_delay * (self.backoff_multiplier ** attempt)
                        time.sleep(delay)
                        continue
            # 청크 단위로 실패해도 전체 실패로 중단하지 않고 가능한 데이터만 사용
            _ = last_error

        return detail_map
    
    def fetch_orders(
        self,
        payment_status: str = "PAYED",
        shipping_status: Optional[str] = "READY",
        place_order_status: Optional[str] = None,
        last_hours: int = 24,
        from_iso: Optional[str] = None,
        to_iso: Optional[str] = None,
        _split_long_range: bool = True,
    ) -> List[Dict]:
        """
        Fetch orders from Naver Commerce API with specified filters.
        
        This method retrieves orders filtered by payment status and optionally
        shipping status or place order status (발주확인). placeOrderStatus is
        response-only in API; when place_order_status is set, shipping_status
        is not sent and results are filtered by placeOrderStatus in response.
        It implements retry logic with exponential backoff for transient failures
        (5xx errors) and raises NaverAPIError for authentication failures (401)
        and other errors.
        
        Args:
            payment_status: Payment status filter (default: "PAYED")
            shipping_status: Shipping status filter (default: "READY"). None 또는 "" 이면 미전송.
            place_order_status: 발주 상태 필터 (예: "OK"=발주확인). 지정 시 shipping_status 미사용, 응답에서 placeOrderStatus로 필터링.
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
                            place_order_status=place_order_status,
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
        # place_order_status 사용 시 API는 필터 미지원이므로 shippingStatus 미전송 후 응답에서 필터링
        if shipping_status and not place_order_status:
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
                
                # 조건형/상세 조회 API 응답에서 항목 리스트 추출
                raw_list = self._extract_raw_list(data)

                if not raw_list:
                    return []

                # place_order_status 모드에서는 productOrderId로 상세 재조회하여
                # 클레임 승인완료/발송 여부를 상세 상태값으로 검증한다.
                detail_map: Dict[str, Dict[str, Any]] = {}
                if place_order_status:
                    ids = [self._extract_product_order_id(item) for item in raw_list]
                    detail_map = self._fetch_order_details_by_ids(ids)

                # API 스키마에 맞게 평탄화: order + productOrder + shippingAddress -> 한 건당 하나의 flat dict
                # contents[] 항목은 { "content": { "order", "productOrder" } } 형태일 수 있음

                orders = []
                for item in raw_list:
                    if not isinstance(item, dict):
                        continue
                    block = item.get("content") if isinstance(item.get("content"), dict) else item
                    order_block = block.get("order") or {}
                    product_order = block.get("productOrder") or {}

                    # place_order_status 모드에서는 상세조회 결과를 우선 사용
                    if place_order_status:
                        product_order_id = self._extract_product_order_id(item)
                        detail = detail_map.get(product_order_id) if product_order_id else None
                        if detail:
                            order_block = detail.get("order") or order_block
                            product_order = detail.get("productOrder") or product_order

                    if product_order:
                        # place_order_status 미사용 시에만 결제상태 필터 적용
                        payment_status_val = (
                            order_block.get("paymentStatus")
                            or product_order.get("paymentStatus")
                            or ""
                        ).strip().upper()
                        if (not place_order_status) and payment_status_val and payment_status_val != "PAYED":
                            continue

                        if place_order_status:
                            # 발주확인(OK)만 포함: placeOrderStatus로 필터 (API 요청 파라미터 미지원이라 응답에서 필터)
                            place_ok = (
                                (product_order.get("placeOrderStatus") or order_block.get("placeOrderStatus") or "")
                            ).strip().upper()
                            if place_ok != place_order_status.upper():
                                continue
                            # 요청 기준: productOrderStatus가 PAYED인 건만 포함
                            product_order_status_val = (
                                product_order.get("productOrderStatus")
                                or order_block.get("productOrderStatus")
                                or ""
                            ).strip().upper()
                            if product_order_status_val != "PAYED":
                                continue
                        else:
                            shipping_status_val = (
                                (
                                    product_order.get("productOrderStatus")
                                    or product_order.get("shippingStatus")
                                    or order_block.get("shippingStatus")
                                    or ""
                                )
                            ).strip().upper()
                            if shipping_status_val and shipping_status_val != "READY":
                                continue
                        buyer_name = (
                            order_block.get("ordererName")
                            or order_block.get("buyerName")
                            or ""
                        )
                        buyer_tel = (
                            order_block.get("ordererTel")
                            or order_block.get("ordererCellphone")
                            or order_block.get("buyerTel")
                            or order_block.get("buyerCellphone")
                            or ""
                        )

                        # 옵션 정보는 배열/객체/문자열 등 다양한 형태일 수 있으므로 유연하게 문자열로 변환
                        raw_option = (
                            product_order.get("optionInfo")
                            or product_order.get("productOption")
                            or product_order.get("option")
                            or ""
                        )
                        option_text = ""
                        if isinstance(raw_option, list):
                            parts = []
                            for opt in raw_option:
                                if isinstance(opt, dict):
                                    name = opt.get("optionName") or opt.get("name")
                                    value = opt.get("optionValue") or opt.get("value")
                                    if name and value:
                                        parts.append(f"{name}:{value}")
                                    elif value:
                                        parts.append(str(value))
                                elif opt is not None:
                                    parts.append(str(opt))
                            option_text = ", ".join(parts)
                        elif isinstance(raw_option, dict):
                            name = raw_option.get("optionName") or raw_option.get("name")
                            value = raw_option.get("optionValue") or raw_option.get("value")
                            if name and value:
                                option_text = f"{name}:{value}"
                            else:
                                option_text = str(value or name or "")
                        elif raw_option:
                            option_text = str(raw_option)

                        # 옵션 정보가 전혀 없으면 상품명으로 폴백
                        if not option_text:
                            option_text = product_order.get("productName") or ""

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
                            "buyerName": buyer_name,
                            "buyerTel": buyer_tel,
                            "optionText": option_text,
                        })
                    else:
                        # 이미 flat 형태(테스트/레거시): 결제완료 + (배송준비중 또는 발주확인)만 포함
                        flat = dict(item)
                        if "orderId" in flat and "order_id" not in flat:
                            flat["order_id"] = flat.get("orderId", "")
                        pay = (flat.get("paymentStatus") or "").upper()
                        if (not place_order_status) and pay and pay != "PAYED":
                            continue

                        if place_order_status:
                            place_ok = (flat.get("placeOrderStatus") or "").upper()
                            if place_ok != place_order_status.upper():
                                continue
                            product_order_status_val = (
                                flat.get("productOrderStatus")
                                or ""
                            ).strip().upper()
                            if product_order_status_val != "PAYED":
                                continue
                        else:
                            ship = (flat.get("shippingStatus") or flat.get("productOrderStatus") or "").upper()
                            if ship and ship != "READY":
                                continue

                        # flat 구조에서도 구매자 정보와 옵션 정보 보강
                        buyer_name = (
                            flat.get("ordererName")
                            or flat.get("buyerName")
                            or ""
                        )
                        buyer_tel = (
                            flat.get("ordererTel")
                            or flat.get("ordererCellphone")
                            or flat.get("buyerTel")
                            or flat.get("buyerCellphone")
                            or ""
                        )
                        raw_option = (
                            flat.get("optionInfo")
                            or flat.get("productOption")
                            or flat.get("option")
                            or ""
                        )
                        option_text = ""
                        if isinstance(raw_option, list):
                            parts = []
                            for opt in raw_option:
                                if isinstance(opt, dict):
                                    name = opt.get("optionName") or opt.get("name")
                                    value = opt.get("optionValue") or opt.get("value")
                                    if name and value:
                                        parts.append(f"{name}:{value}")
                                    elif value:
                                        parts.append(str(value))
                                elif opt is not None:
                                    parts.append(str(opt))
                            option_text = ", ".join(parts)
                        elif isinstance(raw_option, dict):
                            name = raw_option.get("optionName") or raw_option.get("name")
                            value = raw_option.get("optionValue") or raw_option.get("value")
                            if name and value:
                                option_text = f"{name}:{value}"
                            else:
                                option_text = str(value or name or "")
                        elif raw_option:
                            option_text = str(raw_option)

                        if not option_text:
                            option_text = flat.get("productName") or ""

                        flat["buyerName"] = buyer_name
                        flat["buyerTel"] = buyer_tel
                        flat["optionText"] = option_text
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
