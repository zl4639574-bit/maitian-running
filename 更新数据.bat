@echo off
chcp 936 >nul
cd /d "%~dp0"
set PY=C:\Users\15749\.venvs\bib\Scripts\python.exe

echo ============================================
echo  麦田守望长跑队 · 数据中心 —— 更新数据
echo ============================================
echo.

if not exist "%PY%" (
  echo [错误] 找不到 Python: %PY%
  echo 请把本文件里的 PY 改成你电脑上的 python.exe 路径
  pause
  exit /b 1
)

echo [1/2] 读取队伍资料（Excel / Word）...
"%PY%" 提取数据.py
if errorlevel 1 goto fail

echo.
echo [2/2] 压缩照片...
"%PY%" 生成图片.py
if errorlevel 1 goto fail

echo.
echo [完成] 更新好了！打开 index.html 查看（已开着的话按 Ctrl+F5 刷新）
pause
exit /b 0

:fail
echo.
echo [出错] 上面有报错信息，把这一段发给我看
pause
exit /b 1
