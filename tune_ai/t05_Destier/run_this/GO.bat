@echo off
REM GO.bat - ดับเบิลคลิกไฟล์นี้ได้เลย ไม่ต้องเปิด terminal ไม่ต้องพิมพ์ path
REM chcp 65001 = ให้ console อ่านภาษาไทยออก (ไม่งั้นเมนูเป็นตัวยึกยือ)
chcp 65001 >nul
cd /d "%~dp0"
python go.py
pause
