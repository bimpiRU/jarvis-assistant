@echo off
chcp 65001 >nul
cd /d "D:\Projects\jarvis"
echo Запуск Jarvis Assistant...
python main.py
if errorlevel 1 (
    echo.
    echo Ошибка запуска. Убедитесь, что Python добавлен в PATH.
    pause
)
