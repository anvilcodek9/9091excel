"""Order data transformation module for Naver-Logen integration."""

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
    def transform_to_logen_format(orders: List[Dict[str, Any]]) -> List[Dict[str, str]]:
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
                
        Returns:
            List of dictionaries with Logen format fields:
                - receiver_name: Recipient name
                - full_address: Combined address (baseAddress + " " + detailedAddress)
                - receiver_tel: Recipient phone number
                - product_name: Product name
                - delivery_memo: Delivery instructions (empty string if null)
                
        Raises:
            DataTransformError: When required fields are missing, includes order ID
                and missing field name in the error.
        """
        transformed_orders = []
        
        for order in orders:
            # Get order_id for error reporting
            order_id = order.get('order_id', 'unknown')
            
            # Validate required fields
            required_fields = {
                'receiverName': 'receiverName',
                'baseAddress': 'baseAddress',
                'detailedAddress': 'detailedAddress',
                'receiverTel1': 'receiverTel1',
                'productName': 'productName'
            }
            
            for field_key, field_name in required_fields.items():
                if field_key not in order or order[field_key] is None:
                    raise DataTransformError(
                        f"Missing required field: {field_name}",
                        order_id=order_id,
                        missing_field=field_name
                    )
            
            # Transform to Logen format (로젠양식: 주소1, 주소2 분리)
            transformed_order = {
                'receiver_name': order['receiverName'],
                'address1': order['baseAddress'],
                'address2': order['detailedAddress'],
                'full_address': order['baseAddress'] + ' ' + order['detailedAddress'],
                'receiver_tel': order['receiverTel1'],
                'product_name': order['productName'],
                'delivery_memo': order.get('deliveryMemo') or ''
            }
            
            transformed_orders.append(transformed_order)
        
        return transformed_orders
