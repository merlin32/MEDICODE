@echo off
TITLE Dezinstalare MEDICODE
color 0C

echo       AVERTISMENT DEZINSTALARE MEDICODE
echo.
echo Acest script va sterge:
echo  1. Mediul virtual izolat (.venv) si librariile aplicatiei.
echo  2. Modelul medical AI (MedGemma - 2.8 GB) din sistem.
echo.
echo ATENTIE: Python, Ollama si baza ta de date cu analize 
echo NU vor fi sterse automat, pentru siguranta datelor tale.
echo.
set /p choice="Esti sigur ca vrei sa continui? (Y/N): "
if /I "%choice%" NEQ "Y" (
    echo Operatiune anulata.
    pause
    exit /b
)

echo.
echo [PAS 1/2] Stergem modelul AI MedGemma din memoria Ollama...
ollama rm hf.co/gguf-org/medgemma-1.5-4b-it-gguf:Q4_0

echo [PAS 2/2] Stergem mediul virtual (.venv)...
rmdir /s /q .venv

echo.
color 0A
echo  Dezinstalare finalizata cu succes!
echo  Am eliberat spatiul de pe disc. 
echo  Acum poti sterge intregul folder MEDICODE manual.
pause