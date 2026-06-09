@echo off
chcp 65001 > nul
echo =======================================
echo    PNG 피봇 보정 툴 (Pivot Fixer)
echo =======================================
echo.
echo 패키지 설치를 확인합니다...
pip install -r requirements.txt
echo.
echo 프로그램을 실행합니다...
python main.py
pause
