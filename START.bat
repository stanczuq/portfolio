@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
cd /d "%~dp0"
title Portfolio - Patryk Stanczuk

rem --- Python: szukamy "py" (launcher Windows) albo "python" ---
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY ( where python >nul 2>nul && set "PY=python" )

:menu
cls
echo ============================================================
echo   PORTFOLIO  ·  Patryk Stańczuk  ·  sklep VitaForge
echo ============================================================
echo.
echo   [1] Strona portfolio (otwórz w przeglądarce)
echo   [2] Projekt 1: Dashboard sprzedażowy (otwórz)
echo   [3] Projekt 1: Przelicz dane i wygeneruj raport tygodniowy
echo   [4] Projekt 2: Symulator zamówień (podgląd, bez wysyłki)
echo   [5] Projekt 2: Wyślij 20 zamówień testowych do Make
echo   [6] Projekt 3: Asystent AI - czat w przeglądarce
echo   [7] Projekt 3: Testy + ewaluacja (offline, bez klucza)
echo   [8] Projekt 3: Ewaluacja z modelem Claude (wymaga klucza w .env)
echo.
echo   [0] Wyjście
echo.
set /p "c=Wybierz numer: "
if "%c%"=="1" start "" "index.html" & goto menu
if "%c%"=="2" start "" "01-dashboard-sprzedazowy\dashboard\index.html" & goto menu
if "%c%"=="0" exit /b
call :need_python || goto menu
if "%c%"=="3" goto dashboard
if "%c%"=="4" goto sim_dry
if "%c%"=="5" goto sim_send
if "%c%"=="6" goto chat
if "%c%"=="7" goto eval_offline
if "%c%"=="8" goto eval_claude
goto menu

:need_python
if not defined PY (
  echo.
  echo Nie znaleziono Pythona. Zainstaluj Python 3.10+ z https://www.python.org/downloads/
  echo i zaznacz w instalatorze "Add python.exe to PATH". Potem uruchom START.bat ponownie.
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  echo Pierwsze uruchomienie: tworzę środowisko i instaluję biblioteki ^(1-2 min^)...
  %PY% -m venv .venv || ( pause & exit /b 1 )
  ".venv\Scripts\python.exe" -m pip install -q --upgrade pip
  ".venv\Scripts\python.exe" -m pip install -q -r requirements.txt || ( pause & exit /b 1 )
)
set "VPY=%~dp0.venv\Scripts\python.exe"
exit /b 0

:dashboard
pushd "01-dashboard-sprzedazowy"
"%VPY%" run_all.py --skip-generate
popd
start "" "01-dashboard-sprzedazowy\dashboard\index.html"
pause & goto menu

:sim_dry
pushd "02-automatyzacja-zamowien-make"
"%VPY%" simulator\send_orders.py --scenario mix --count 12
popd
pause & goto menu

:sim_send
pushd "02-automatyzacja-zamowien-make"
if not exist ".env" (
  echo Brak pliku .env z adresem webhooka Make. Skopiuj .env.example do .env i uzupełnij.
  popd & pause & goto menu
)
"%VPY%" simulator\send_orders.py --scenario mix --count 20
popd
pause & goto menu

:chat
pushd "03-asystent-ai-obslugi-klienta"
echo Asystent startuje na http://localhost:8000  (zamknij to okno, żeby go wyłączyć)
start "" "http://localhost:8000"
"%VPY%" -m uvicorn api.server:app --port 8000
popd
pause & goto menu

:eval_offline
pushd "03-asystent-ai-obslugi-klienta"
"%VPY%" -m pytest -q
"%VPY%" eval\run_eval.py --mode offline
"%VPY%" eval\run_eval.py --mode offline --cases cases_holdout
popd
pause & goto menu

:eval_claude
pushd "03-asystent-ai-obslugi-klienta"
if not exist ".env" (
  copy ".env.example" ".env" >nul
  echo Utworzyłem plik .env. Wpisz w nim swój klucz ANTHROPIC_API_KEY, zapisz i wybierz [8] ponownie.
  notepad ".env"
  popd & pause & goto menu
)
"%VPY%" eval\run_eval.py --mode claude
"%VPY%" eval\run_eval.py --mode claude --cases cases_holdout
"%VPY%" eval\update_readme.py
popd
pause & goto menu
