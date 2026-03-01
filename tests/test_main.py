"""Unit tests for main function."""

import os
import pytest
from unittest.mock import patch, MagicMock

# Mock platform check before importing
with patch('platform.system', return_value='Windows'):
    from src.main import generate_logen_shipping_file
    from src.exceptions import NaverAPIError, DataTransformError, ExcelGenerationError


class TestGenerateLogenShippingFile:
    """Test suite for generate_logen_shipping_file function."""
    
    def test_main_function_with_access_token_parameter(self):
        """Test main function accepts access token as parameter."""
        with patch('src.main.ensure_windows_platform'), \
             patch('src.main.NaverCommerceClient') as mock_client_class, \
             patch('src.main.OrderTransformer.transform_to_logen_format') as mock_transform, \
             patch('src.main.LogenExcelGenerator.generate_excel') as mock_excel, \
             patch('src.main.generate_logen_filename') as mock_filename:
            
            # Setup mocks
            mock_client = MagicMock()
            mock_client.fetch_orders.return_value = [{'order_id': '123'}]
            mock_client_class.return_value = mock_client
            
            mock_transform.return_value = [{'receiver_name': 'Test'}]
            mock_filename.return_value = '로젠발송양식_20240115.xlsx'
            mock_excel.return_value = '로젠발송양식_20240115.xlsx'
            
            # Execute
            result = generate_logen_shipping_file(access_token='test_token')
            
            # Verify
            mock_client_class.assert_called_once_with('test_token')
            mock_client.fetch_orders.assert_called_once()
            mock_transform.assert_called_once_with([{'order_id': '123'}])
            mock_excel.assert_called_once()
            assert result == '로젠발송양식_20240115.xlsx'
    
    def test_main_function_reads_from_environment_variable(self):
        """Test main function reads access token from environment variable."""
        with patch('src.main.ensure_windows_platform'), \
             patch('src.main.NaverCommerceClient') as mock_client_class, \
             patch('src.main.OrderTransformer.transform_to_logen_format') as mock_transform, \
             patch('src.main.LogenExcelGenerator.generate_excel') as mock_excel, \
             patch('src.main.generate_logen_filename') as mock_filename, \
             patch.dict(os.environ, {'NAVER_ACCESS_TOKEN': 'env_token'}):
            
            # Setup mocks
            mock_client = MagicMock()
            mock_client.fetch_orders.return_value = []
            mock_client_class.return_value = mock_client
            
            mock_transform.return_value = []
            mock_filename.return_value = '로젠발송양식_20240115.xlsx'
            mock_excel.return_value = '로젠발송양식_20240115.xlsx'
            
            # Execute
            result = generate_logen_shipping_file()
            
            # Verify
            mock_client_class.assert_called_once_with('env_token')

    def test_main_function_auto_issues_token_with_client_id_secret(self):
        """Test main function auto-issues token when NAVER_CLIENT_ID and NAVER_CLIENT_SECRET are set."""
        with patch('src.main.ensure_windows_platform'), \
             patch('src.main.NaverCommerceClient') as mock_client_class, \
             patch('src.main.OrderTransformer.transform_to_logen_format') as mock_transform, \
             patch('src.main.LogenExcelGenerator.generate_excel') as mock_excel, \
             patch('src.main.generate_logen_filename') as mock_filename, \
             patch('src.auth.get_access_token', return_value='auto_issued_token'), \
             patch.dict(os.environ, {
                 'NAVER_CLIENT_ID': 'test_client_id',
                 'NAVER_CLIENT_SECRET': 'test_client_secret',
             }, clear=True):
            mock_client = MagicMock()
            mock_client.fetch_orders.return_value = []
            mock_client_class.return_value = mock_client
            mock_transform.return_value = []
            mock_filename.return_value = '로젠발송양식_20240115.xlsx'
            mock_excel.return_value = '로젠발송양식_20240115.xlsx'

            result = generate_logen_shipping_file()

            # resolve_access_token calls get_access_token when only client_id/secret exist
            mock_client_class.assert_called_once_with('auto_issued_token')
            assert result == '로젠발송양식_20240115.xlsx'
    
    def test_main_function_raises_error_when_no_token(self):
        """Test main function raises ValueError when no access token provided."""
        with patch('src.main.ensure_windows_platform'), \
             patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                generate_logen_shipping_file()
            
            assert "NAVER_ACCESS_TOKEN" in str(exc_info.value) or "액세스 토큰" in str(exc_info.value)
    
    def test_main_function_propagates_naver_api_error(self):
        """Test main function propagates NaverAPIError from API client."""
        with patch('src.main.ensure_windows_platform'), \
             patch('src.main.NaverCommerceClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.fetch_orders.side_effect = NaverAPIError("API Error")
            mock_client_class.return_value = mock_client
            
            with pytest.raises(NaverAPIError):
                generate_logen_shipping_file(access_token='test_token')
    
    def test_main_function_propagates_data_transform_error(self):
        """Test main function propagates DataTransformError from transformer."""
        with patch('src.main.ensure_windows_platform'), \
             patch('src.main.NaverCommerceClient') as mock_client_class, \
             patch('src.main.OrderTransformer.transform_to_logen_format') as mock_transform:
            
            mock_client = MagicMock()
            mock_client.fetch_orders.return_value = [{'order_id': '123'}]
            mock_client_class.return_value = mock_client
            
            mock_transform.side_effect = DataTransformError("Transform Error")
            
            with pytest.raises(DataTransformError):
                generate_logen_shipping_file(access_token='test_token')
    
    def test_main_function_propagates_excel_generation_error(self):
        """Test main function propagates ExcelGenerationError from generator."""
        with patch('src.main.ensure_windows_platform'), \
             patch('src.main.NaverCommerceClient') as mock_client_class, \
             patch('src.main.OrderTransformer.transform_to_logen_format') as mock_transform, \
             patch('src.main.LogenExcelGenerator.generate_excel') as mock_excel, \
             patch('src.main.generate_logen_filename') as mock_filename:
            
            mock_client = MagicMock()
            mock_client.fetch_orders.return_value = [{'order_id': '123'}]
            mock_client_class.return_value = mock_client
            
            mock_transform.return_value = [{'receiver_name': 'Test'}]
            mock_filename.return_value = '로젠발송양식_20240115.xlsx'
            mock_excel.side_effect = ExcelGenerationError("Excel Error")
            
            with pytest.raises(ExcelGenerationError):
                generate_logen_shipping_file(access_token='test_token')
    
    def test_main_function_executes_workflow_in_correct_order(self):
        """Test main function executes workflow steps in correct order."""
        call_order = []
        
        with patch('src.main.ensure_windows_platform'), \
             patch('src.main.NaverCommerceClient') as mock_client_class, \
             patch('src.main.OrderTransformer.transform_to_logen_format') as mock_transform, \
             patch('src.main.LogenExcelGenerator.generate_excel') as mock_excel, \
             patch('src.main.generate_logen_filename') as mock_filename:
            
            # Setup mocks to track call order
            mock_client = MagicMock()
            def fetch_orders_side_effect(*args, **kwargs):
                call_order.append('fetch_orders')
                return [{'order_id': '123'}]
            mock_client.fetch_orders.side_effect = fetch_orders_side_effect
            mock_client_class.return_value = mock_client
            
            def transform_side_effect(orders):
                call_order.append('transform')
                return [{'receiver_name': 'Test'}]
            mock_transform.side_effect = transform_side_effect
            
            def excel_side_effect(data, path):
                call_order.append('generate_excel')
                return path
            mock_excel.side_effect = excel_side_effect
            
            mock_filename.return_value = '로젠발송양식_20240115.xlsx'
            
            # Execute
            generate_logen_shipping_file(access_token='test_token')
            
            # Verify order
            assert call_order == ['fetch_orders', 'transform', 'generate_excel']
