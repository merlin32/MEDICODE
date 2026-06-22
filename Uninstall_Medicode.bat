@echo off
TITLE Dezinstalare MEDICODE - Clean Up Utility
color 0C

REM Ne asiguram ca scriptul ruleaza strict din folderul proiectului
cd /d "%~dp0"

echo =========================================================
echo       UTILITAR DE DEZINSTALARE SYSTEM MEDICODE
echo =========================================================
echo.
echo Bine ai venit in meniul de dezinstalare. 
echo Te rugam sa alegi ce componente doresti sa elimini de pe sistem.
echo Raspunde cu Y (Da) sau N (Nu) la urmatoarele intrebari:
echo.

set /p del_core="1. Stergem fisierele aplicatiei .venv si modelul AI MedGemma? Y/N: "
set /p del_db="2. Stergem BAZA DE DATE (istoricul si analizele)? Datele nu pot fi recuperate! Y/N: "
set /p del_ollama="3. Dezinstalam complet motorul AI Ollama de pe PC? Y/N: "

echo.
echo =========================================================
echo                INCEPEM PROCESUL...
echo =========================================================

if /I "%del_core%" EQU "Y" (
    echo.
    echo [1/3] Curatam componentele de baza MEDICODE...
    ollama rm hf.co/gguf-org/medgemma-1.5-4b-it-gguf:Q4_0 >nul 2>&1
    echo   -^> Modelul AI a fost sters.
    if exist ".venv" (
        rmdir /s /q .venv
        echo   -^> Mediul virtual .venv a fost sters complet.
    )
) ELSE (
    echo.
    echo [1/3] Componentele de baza au fost pastrate.
)

if /I "%del_db%" EQU "Y" (
    echo.
    echo [2/3] Stergem baza de date locala...
    if exist "data\database" (
        rmdir /s /q "data\database"
        echo   -^> [SUCCES] Baza de date si istoricul pacientilor au fost sterse.
    ) ELSE (
        echo   -^> [INFO] Nu s-a gasit nicio baza de date in sistem.
    )
) ELSE (
    echo.
    echo [2/3] Baza de date a fost pastrata in siguranta.
)

if /I "%del_ollama%" EQU "Y" (
    echo.
    echo [3/3] Dezinstalam aplicatia Ollama...
    taskkill /f /im "ollama app.exe" >nul 2>&1
    taskkill /f /im "ollama.exe" >nul 2>&1
    
    echo   -^> Cautam aplicatia via Windows Package Manager...
    
    REM Metoda 1: Forțare prin winget (standard pe Windows 10/11)
    winget uninstall --id Ollama.Ollama --silent --accept-source-agreements >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        echo   -^> [SUCCES] Ollama a fost eliminat automat prin winget!
        goto ollama_done
    )

    REM Metoda 2: Căutare fișiere fizice ascunse
    if exist "%LOCALAPPDATA%\Programs\Ollama\uninstall.exe" (
        start /wait "" "%LOCALAPPDATA%\Programs\Ollama\uninstall.exe" /S
        echo   -^> [SUCCES] Ollama a fost eliminat din AppData.
        goto ollama_done
    )
    if exist "%LOCALAPPDATA%\Ollama\uninstall.exe" (
        start /wait "" "%LOCALAPPDATA%\Ollama\uninstall.exe" /S
        echo   -^> [SUCCES] Ollama a fost eliminat din AppData local.
        goto ollama_done
    )
    
    REM Metoda 3: Asistență vizuală directă
    echo   -^> [INFO] Ollama foloseste sistemul de pachete invizibil din Windows.
    echo   -^> Iti deschidem automat fereastra cu aplicatiile sistemului.
    echo   -^> Cauta "Ollama" in lista care apare si da click pe Uninstall!
    start ms-settings:appsfeatures

    :ollama_done
    echo.
) ELSE (
    echo.
    echo [3/3] Ollama a fost pastrat pe sistem.
)

echo.
color 0A
echo =========================================================
echo             OPERATIUNE FINALIZATA!
echo =========================================================
echo Procesul de curatare a luat sfarsit.
echo Acum poti sterge intregul folder MEDICODE manual daca doresti.
pause