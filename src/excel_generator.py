"""Excel file generator for Logen delivery format."""

from typing import List, Dict
from openpyxl import Workbook

from .exceptions import ExcelGenerationError


class LogenExcelGenerator:
    """Generator for Logen delivery Excel files."""
    
    @staticmethod
    def generate_excel(data: List[Dict], output_path: str) -> str:
        """
        Generate Logen shipping Excel file.
        
        Creates an Excel workbook with a header row and data rows for each
        transformed order in Logen's required format.
        
        Args:
            data: List of transformed order dictionaries with keys:
                - receiver_name: 받는사람
                - full_address: 주소
                - receiver_tel: 전화번호
                - product_name: 상품명
                - delivery_memo: 배송메모
            output_path: Path for output Excel file
            
        Returns:
            str: Path to generated file
            
        Raises:
            ExcelGenerationError: When file creation fails due to file system
                errors or other issues
        """
        try:
            # Create workbook
            wb = Workbook()
            ws = wb.active
            
            # Create header row
            headers = ["받는사람", "주소", "전화번호", "상품명", "배송메모"]
            ws.append(headers)
            
            # Create data rows starting from row 2
            for order in data:
                row = [
                    order.get("receiver_name", ""),
                    order.get("full_address", ""),
                    order.get("receiver_tel", ""),
                    order.get("product_name", ""),
                    order.get("delivery_memo", "")
                ]
                ws.append(row)
            
            # Save workbook
            wb.save(output_path)
            
            return output_path
            
        except Exception as e:
            raise ExcelGenerationError(
                message=f"Failed to generate Excel file",
                file_path=output_path,
                underlying_error=e
            )
