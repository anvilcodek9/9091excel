"""Order data transformation module for Naver-Logen integration."""

import re
from typing import List, Dict, Any
from src.exceptions import DataTransformError


class OrderTransformer:
    """
    Transforms Naver Commerce order data to Logen delivery format.
    
    This class handles the conversion of order data from Naver Smart Store
    format to the format required by Logen delivery service, including
    field validation, mapping, and address concatenation.
    """
    
    @staticmethod
    def _extract_arrival_text(option_text: str) -> str:
        """
        Extract arrival schedule text that follows "도착일:" marker.

        - Accepts variations like "도 착 일:", "도착 일:"
        - Stops before next option token such as "/ 옵션명:..."
        """
        if not option_text:
            return ""

        matched = re.search(
            r"도\s*착\s*일\s*[:：]\s*(.+?)(?=\s*/\s*[^/]+[:：]|$)",
            option_text,
        )
        if not matched:
            return ""
        return matched.group(1).strip()

    @staticmethod
    def _build_delivery_memo(option_text: str, original_memo: str) -> str:
        """
        Build delivery memo from arrival text in option info and original memo.
        """
        arrival_text = OrderTransformer._extract_arrival_text(option_text)
        arrival_with_key = f"도착일: {arrival_text}" if arrival_text else ""
        if arrival_with_key and original_memo:
            return f"{arrival_with_key} | {original_memo}"
        if arrival_with_key:
            return arrival_with_key
        return original_memo

    @staticmethod
    def transform_to_logen_format(
        orders: List[Dict[str, Any]], 
        exclude_keywords: List[str] = None
    ) -> List[Dict[str, str]]:
        """
        Transform Naver orders to Logen delivery format.
        
        Validates required fields, maps fields directly, concatenates address fields,
        and handles optional fields appropriately.
        
        Args:
            orders: List of Naver order dictionaries with fields:
                - order_id: Unique order identifier
                - receiverName: Recipient name
                - baseAddress: Primary address
                - detailedAddress: Secondary address (apartment number, etc.)
                - receiverTel1: Recipient phone number
                - productName: Product name
                - deliveryMemo: Delivery instructions (optional)
                - buyerName: Buyer name (구매자명, 보내는 분)
                - buyerTel: Buyer phone (구매자 연락처, 보내는 분 연락처)
                - optionText: Option information text (옵션정보)
                
        Returns:
            List of dictionaries with Logen format fields:
                - receiver_name: Recipient name
                - full_address: Combined address (baseAddress + " " + detailedAddress)
                - receiver_tel: Recipient phone number
                - product_name: Product name + option text (상품명 + 옵션정보)
                - delivery_memo: "도착일: 이후 텍스트 + 기존 배송메세지" 형식
                - sender_name: Buyer name (보내는 분)
                - sender_tel: Buyer phone (보내는 분 연락처)
                
        Raises:
            DataTransformError: When required fields are missing, includes order ID
                and missing field name in the error.
        """
        transformed_orders = []
        
        for order in orders:
            # Get order_id for error reporting
            order_id = order.get('order_id', 'unknown')
            
            # Validate required 필드 (수취인/주소/상품명)
            required_fields = {
                'receiverName': 'receiverName',
                'baseAddress': 'baseAddress',
                'detailedAddress': 'detailedAddress',
                'receiverTel1': 'receiverTel1',
                'productName': 'productName',
            }

            for field_key, field_name in required_fields.items():
                if field_key not in order or order[field_key] is None:
                    raise DataTransformError(
                        f"Missing required field: {field_name}",
                        order_id=order_id,
                        missing_field=field_name,
                    )

            # 구매자(보내는 분) 정보 및 옵션정보 처리
            buyer_name = order.get('buyerName') or order.get('ordererName') or ''
            buyer_tel = (
                order.get('buyerTel')
                or order.get('ordererTel')
                or order.get('ordererCellphone')
                or ''
            )

            option_text = (order.get('optionText') or '').strip()
            product_name = (order.get('productName') or '').strip()

            # 품목명: "상품명 + 옵션정보" 형태 (옵션 없으면 상품명만)
            if option_text:
                product_for_logen = f"{product_name} {option_text}".strip()
            else:
                product_for_logen = product_name
            
            # 지정된 키워드 제거
            if exclude_keywords:
                for keyword in exclude_keywords:
                    product_for_logen = product_for_logen.replace(keyword, "")
                # 연속된 띄어쓰기를 단일 띄어쓰기로 정리하고 좌우 공백 제거
                product_for_logen = " ".join(product_for_logen.split())

            # 배송메시지: 옵션정보에서 "도착일:" 이후 텍스트 + 기존 배송메시지
            original_memo = (order.get('deliveryMemo') or '').strip()
            delivery_memo_for_logen = OrderTransformer._build_delivery_memo(
                option_text=option_text,
                original_memo=original_memo,
            )

            # Transform to Logen format (로젠양식: 주소1, 주소2 분리)
            transformed_order = {
                'receiver_name': order['receiverName'],
                'address1': order['baseAddress'],
                'address2': order['detailedAddress'],
                'full_address': order['baseAddress'] + ' ' + order['detailedAddress'],
                'receiver_tel': order['receiverTel1'],
                'product_name': product_for_logen,
                'delivery_memo': delivery_memo_for_logen,
                'buyer_name': buyer_name,
                'buyer_tel': buyer_tel,
                'sender_name': buyer_name,
                'sender_tel': buyer_tel,
            }
            
            transformed_orders.append(transformed_order)
        
        return transformed_orders
