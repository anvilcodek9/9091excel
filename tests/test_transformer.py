"""Unit tests for OrderTransformer."""

import pytest
from src.transformer import OrderTransformer
from src.exceptions import DataTransformError


def test_transform_basic_order():
    """Test basic order transformation with all required fields."""
    orders = [{
        'order_id': 'ORDER123',
        'receiverName': '김철수',
        'baseAddress': '서울시 강남구',
        'detailedAddress': '101동 202호',
        'receiverTel1': '010-1234-5678',
        'productName': '테스트 상품',
        'deliveryMemo': '문 앞에 놓아주세요'
    }]
    
    result = OrderTransformer.transform_to_logen_format(orders)
    
    assert len(result) == 1
    assert result[0]['receiver_name'] == '김철수'
    assert result[0]['full_address'] == '서울시 강남구 101동 202호'
    assert result[0]['receiver_tel'] == '010-1234-5678'
    assert result[0]['product_name'] == '테스트 상품'
    assert result[0]['delivery_memo'] == '문 앞에 놓아주세요'


def test_transform_null_delivery_memo():
    """Test that null deliveryMemo is converted to empty string."""
    orders = [{
        'order_id': 'ORDER123',
        'receiverName': '김철수',
        'baseAddress': '서울시 강남구',
        'detailedAddress': '101동 202호',
        'receiverTel1': '010-1234-5678',
        'productName': '테스트 상품',
        'deliveryMemo': None
    }]
    
    result = OrderTransformer.transform_to_logen_format(orders)
    
    assert result[0]['delivery_memo'] == ''


def test_transform_missing_delivery_memo():
    """Test that missing deliveryMemo field is converted to empty string."""
    orders = [{
        'order_id': 'ORDER123',
        'receiverName': '김철수',
        'baseAddress': '서울시 강남구',
        'detailedAddress': '101동 202호',
        'receiverTel1': '010-1234-5678',
        'productName': '테스트 상품'
    }]
    
    result = OrderTransformer.transform_to_logen_format(orders)
    
    assert result[0]['delivery_memo'] == ''


def test_transform_missing_receiver_name():
    """Test that missing receiverName raises DataTransformError."""
    orders = [{
        'order_id': 'ORDER123',
        'baseAddress': '서울시 강남구',
        'detailedAddress': '101동 202호',
        'receiverTel1': '010-1234-5678',
        'productName': '테스트 상품'
    }]
    
    with pytest.raises(DataTransformError) as exc_info:
        OrderTransformer.transform_to_logen_format(orders)
    
    assert exc_info.value.order_id == 'ORDER123'
    assert exc_info.value.missing_field == 'receiverName'


def test_transform_missing_base_address():
    """Test that missing baseAddress raises DataTransformError."""
    orders = [{
        'order_id': 'ORDER456',
        'receiverName': '김철수',
        'detailedAddress': '101동 202호',
        'receiverTel1': '010-1234-5678',
        'productName': '테스트 상품'
    }]
    
    with pytest.raises(DataTransformError) as exc_info:
        OrderTransformer.transform_to_logen_format(orders)
    
    assert exc_info.value.order_id == 'ORDER456'
    assert exc_info.value.missing_field == 'baseAddress'


def test_transform_missing_detailed_address():
    """Test that missing detailedAddress raises DataTransformError."""
    orders = [{
        'order_id': 'ORDER789',
        'receiverName': '김철수',
        'baseAddress': '서울시 강남구',
        'receiverTel1': '010-1234-5678',
        'productName': '테스트 상품'
    }]
    
    with pytest.raises(DataTransformError) as exc_info:
        OrderTransformer.transform_to_logen_format(orders)
    
    assert exc_info.value.order_id == 'ORDER789'
    assert exc_info.value.missing_field == 'detailedAddress'


def test_transform_missing_receiver_tel():
    """Test that missing receiverTel1 raises DataTransformError."""
    orders = [{
        'order_id': 'ORDER101',
        'receiverName': '김철수',
        'baseAddress': '서울시 강남구',
        'detailedAddress': '101동 202호',
        'productName': '테스트 상품'
    }]
    
    with pytest.raises(DataTransformError) as exc_info:
        OrderTransformer.transform_to_logen_format(orders)
    
    assert exc_info.value.order_id == 'ORDER101'
    assert exc_info.value.missing_field == 'receiverTel1'


def test_transform_missing_product_name():
    """Test that missing productName raises DataTransformError."""
    orders = [{
        'order_id': 'ORDER202',
        'receiverName': '김철수',
        'baseAddress': '서울시 강남구',
        'detailedAddress': '101동 202호',
        'receiverTel1': '010-1234-5678'
    }]
    
    with pytest.raises(DataTransformError) as exc_info:
        OrderTransformer.transform_to_logen_format(orders)
    
    assert exc_info.value.order_id == 'ORDER202'
    assert exc_info.value.missing_field == 'productName'


def test_transform_multiple_orders():
    """Test transformation of multiple orders."""
    orders = [
        {
            'order_id': 'ORDER1',
            'receiverName': '김철수',
            'baseAddress': '서울시 강남구',
            'detailedAddress': '101동 202호',
            'receiverTel1': '010-1234-5678',
            'productName': '상품1'
        },
        {
            'order_id': 'ORDER2',
            'receiverName': '이영희',
            'baseAddress': '부산시 해운대구',
            'detailedAddress': '303동 404호',
            'receiverTel1': '010-9876-5432',
            'productName': '상품2',
            'deliveryMemo': '배송 전 연락주세요'
        }
    ]
    
    result = OrderTransformer.transform_to_logen_format(orders)
    
    assert len(result) == 2
    assert result[0]['receiver_name'] == '김철수'
    assert result[0]['full_address'] == '서울시 강남구 101동 202호'
    assert result[0]['delivery_memo'] == ''
    assert result[1]['receiver_name'] == '이영희'
    assert result[1]['full_address'] == '부산시 해운대구 303동 404호'
    assert result[1]['delivery_memo'] == '배송 전 연락주세요'


def test_transform_address_concatenation_with_space():
    """Test that address concatenation includes exactly one space."""
    orders = [{
        'order_id': 'ORDER303',
        'receiverName': '박민수',
        'baseAddress': '대구시 중구',
        'detailedAddress': '505동',
        'receiverTel1': '010-5555-6666',
        'productName': '테스트'
    }]
    
    result = OrderTransformer.transform_to_logen_format(orders)
    
    # Verify exactly one space between addresses
    assert result[0]['full_address'] == '대구시 중구 505동'
    assert '  ' not in result[0]['full_address']  # No double spaces


def test_transform_delivery_memo_extracts_arrival_text_from_option():
    """도착일 패턴이 있을 때만 옵션에서 배송일정을 배송메모로 추가한다."""
    orders = [{
        'order_id': 'ORDER404',
        'receiverName': '홍길동',
        'baseAddress': '서울시 송파구',
        'detailedAddress': '10동 1001호',
        'receiverTel1': '010-1111-2222',
        'productName': '사과',
        'optionText': '색상:레드 / 도 착 일: 3/25(월) 도착 예정 / 수량:1개',
        'deliveryMemo': '부재시 문앞'
    }]

    result = OrderTransformer.transform_to_logen_format(orders)

    assert result[0]['delivery_memo'] == '도착일: 3/25(월) 도착 예정 | 부재시 문앞'


def test_transform_delivery_memo_ignores_non_arrival_last_option():
    """마지막 옵션이 도착일이 아니면 기존 배송메모만 유지한다."""
    orders = [{
        'order_id': 'ORDER505',
        'receiverName': '홍길동',
        'baseAddress': '서울시 송파구',
        'detailedAddress': '10동 1001호',
        'receiverTel1': '010-1111-2222',
        'productName': '사과',
        'optionText': '색상:레드 / 잘못된정보 / 수량:1개',
        'deliveryMemo': '문앞'
    }]

    result = OrderTransformer.transform_to_logen_format(orders)

    assert result[0]['delivery_memo'] == '문앞'
