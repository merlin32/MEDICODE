@echo off
TITLE MEDICODE - Auto-Installer & Launcher
color 0B

echo     Pornire Sistem MEDICODE (Diagnostic AI)
echo.

python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    color 0E
    echo [PAS 1/5] Python nu a fost gasit. Il descarcam si instalam automat...
    echo Te rugam sa astepti (poate dura 1-2 minute). Nu inchide fereastra!
    powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe' -OutFile 'python_installer.exe'"
    :: Instalam Python silentios pentru utilizatorul curent si il adaugam in PATH
    start /wait python_installer.exe /quiet InstallAllUsers=0 PrependPath=1 Include_test=0
    del python_installer.exe
    
    echo.
    echo [SUCCES] Python a fost instalat! Este necesar un restart rapid al ferestrei.
    echo Te rog sa inchizi aceasta fereastra si sa dai DUBLU-CLICK din nou pe Start_Medicode.bat
    pause
    exit /b
)

ollama --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    color 0E
    echo [PAS 2/5] Motorul AI (Ollama) nu a fost gasit. Il descarcam si instalam...
    powershell -Command "Invoke-WebRequest -Uri 'https://ollama.com/download/OllamaSetup.exe' -OutFile 'OllamaSetup.exe'"
    :: Instalam Ollama silentios
    start /wait OllamaSetup.exe /S
    del OllamaSetup.exe
    echo [SUCCES] Ollama a fost instalat!
)

IF NOT EXIST ".venv\Scripts\activate.bat" (
    echo [PAS 3/5] Cream mediul izolat pentru aplicatie...
    py -3.11 -m venv .venv
)

call .venv\Scripts\activate.bat

echo [PAS 4/5] Verificam si instalam librariile necesare (din requirements.txt)...
pip install -r requirements.txt --quiet

echo [PAS 5/5] Verificam inteligenta artificiala medicala (MedGemma)...
echo (Daca este prima data, va descarca modelul si vei vedea progresul mai jos)
ollama pull hf.co/gguf-org/medgemma-1.5-4b-it-gguf:Q4_0

color 0A
echo.
echo     Toate sistemele sunt functionale!
echo     Lansam platforma MEDICODE in browser...
echo.
echo Apasa CTRL+C in aceasta fereastra cand vrei sa opresti aplicatia.
echo.

streamlit run src/frontend/interfata.py

pause