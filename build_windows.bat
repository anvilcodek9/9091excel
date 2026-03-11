@echo off
chcp 65001 >nul
echo ========================================
echo   LogenExcel Windows 빌드 스크립트
echo ========================================
echo.

REM Python 확인
where python >nul 2>&1
if %errorlevel% neq 0 (
    where py >nul 2>&1
    if %errorlevel% neq 0 (
        echo [오류] Python이 설치되어 있지 않거나 PATH에 없습니다.
        echo Python 3.9 이상을 설치한 후 다시 시도하세요.
        echo https://www.python.org/downloads/
        pause
        exit /b 1
    )
    set PYTHON_CMD=py
) else (
    set PYTHON_CMD=python
)

echo [1/3] 빌드 의존성 설치 중...
%PYTHON_CMD% -m pip install -r requirements-build.txt
if %errorlevel% neq 0 (
    echo [오류] 의존성 설치 실패
    pause
    exit /b 1
)

echo.
echo [2/3] PyInstaller로 exe 빌드 중...
echo.
%PYTHON_CMD% -m PyInstaller logen_excel.spec --noconfirm
if %errorlevel% neq 0 (
    echo [오류] 빌드 실패
    pause
    exit /b 1
)

echo.
echo ========================================
echo   빌드 완료!
echo ========================================
echo.
echo 생성된 파일: dist\LogenExcel.exe
echo.
echo 실행 방법:
echo   dist\LogenExcel.exe
echo   dist\LogenExcel.exe --hours 12
echo   dist\LogenExcel.exe --from "2024-03-01T00:00:00" --to "2024-03-02T00:00:00"
echo.
pause
