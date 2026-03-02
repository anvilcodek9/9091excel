"""Excel file generator for Logen delivery format."""

from typing import List, Dict
from openpyxl import Workbook

from .exceptions import ExcelGenerationError

# 로젠양식: 엑셀파일첫행-제목있음(주소1,2로분리)
LOGEN_HEADERS = [
    "수하인명",
    "운송장번호(로젠택배)",
    "수하인주소1",
    "수하인주소2",
    "수하인전화번호",
    "수하인핸드폰번호",
    "택배수량",
    "택배운임",
    "운임구분",
    "품목명",
    "",
    "배송메세지 (도착일)",
    "보내는 분",
    "연락처",
    "주소",
]
LOGEN_SHEET_NAME = "엑셀파일첫행-제목있음(주소1,2로분리)"


class LogenExcelGenerator:
    """Generator for Logen delivery Excel files."""
    
    @staticmethod
    def generate_excel(data: List[Dict], output_path: str) -> str:
        """
        Generate Logen shipping Excel file.
        
        Creates an Excel workbook in Logen format (로젠양식.xls) with 15 columns.
        
        Args:
            data: List of transformed order dictionaries with keys:
                - receiver_name: 수하인명
                - address1: 수하인주소1 (baseAddress)
                - address2: 수하인주소2 (detailedAddress)
                - receiver_tel: 수하인전화번호
                - product_name: 품목명
                - delivery_memo: 배송메세지 (도착일)
            output_path: Path for output Excel file
            
        Returns:
            str: Path to generated file
            
        Raises:
            ExcelGenerationError: When file creation fails due to file system
                errors or other issues
        """
        try:
            wb = Workbook()
            ws = wb.active
            ws.title = LOGEN_SHEET_NAME
            
            # Create header row (로젠양식 15열)
            ws.append(LOGEN_HEADERS)
            
            # Create data rows
            for order in data:
                address1 = order.get("address1", "")
                address2 = order.get("address2", "")
                if not address1 and not address2:
                    full = order.get("full_address", "")
                    address1, address2 = (full, "") if full else ("", "")
                
                row = [
                    order.get("receiver_name", ""),
                    "",  # 운송장번호(로젠택배) - 택배사에서 채움
                    address1,
                    address2,
                    order.get("receiver_tel", ""),
                    order.get("receiver_tel", ""),  # 수하인핸드폰번호
                    1,  # 택배수량
                    "",  # 택배운임
                    "",  # 운임구분
                    order.get("product_name", ""),
                    "",  # 빈 열
                    order.get("delivery_memo", ""),
                    "",  # 보내는 분
                    "",  # 연락처
                    "",  # 주소 (보내는 분 주소)
                ]
                ws.append(row)
            
            wb.save(output_path)
            return output_path
            
        except Exception as e:
            raise ExcelGenerationError(
                message=f"Failed to generate Excel file",
                file_path=output_path,
                underlying_error=e
            )
