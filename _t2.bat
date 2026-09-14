@echo off
chcp 936 >nul
title 麦田守望数据中心 - 更新数据并上传
cd /d "%~dp0"

set PY=C:\Users\15749\.venvs\bib\Scripts\python.exe
if not exist "%PY%" set PY=python

echo ============================================================
echo   更新数据并上传到线上
echo   网址：https://zl4639574-bit.github.io/maitian-running/
echo ============================================================
echo.
echo [1/4] 读取队伍资料（E:\Desktop\麦田 里的 Excel / Word）...
"%PY%" 提取数据.py
if errorlevel 1 goto fail

echo.
echo [2/4] 压缩整理照片...
"%PY%" 生成图片.py
if errorlevel 1 goto fail

echo.
echo [3/4] 记录改动...
git add -A
git diff --cached --quiet
if errorlevel 1 (
  git -c user.name="麦田守望" -c user.email="maitian@local" commit -m "更新队伍数据" >nul
  echo   已记录本次改动
) else (
  echo   没有发现新的改动
)

echo.
echo [4/4] 上传到 GitHub（约 10 秒）...
git push origin master
if errorlevel 1 goto pushfail

echo.
echo ============================================================
echo   完成！约 1 分钟后三个网址都是新数据：
echo     https://zl4639574-bit.github.io/maitian-running/
echo     https://zl4639574-bit.github.io/maitian-running/member/
echo     https://zl4639574-bit.github.io/maitian-running/captain/
echo ============================================================
pause
exit /b 0

:pushfail
echo.
echo [!] 上传失败 —— 通常是网络问题。
echo     开一下 VPN，然后再双击一次本文件即可（已经生成的数据不会丢）。
pause
exit /b 1

:fail
echo.
echo [出错] 上面有报错信息，把这一段发给我看
pause
exit /b 1
