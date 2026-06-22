@echo off
TITLE MEDICODE - Auto-Installer ^& Launcher
color 0B

REM Ne asiguram ca scriptul ruleaza strict din folderul proiectului
cd /d "%~dp0"

echo     Pornire Sistem MEDICODE - Diagnostic AI
echo.

echo [PAS 1/5] Verificam versiunea corecta de Python 3.11...
py -3.11 --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    color 0E
    echo   -^> Python 3.11 nu a fost gasit.
    echo   -^> Il instalam in paralel, fara sa stricam versiunile actuale...
    curl -L "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe" -o "python_installer.exe"
    
    REM PrependPath=0 asigura ca Python 3.11 NU suprascrie versiunea principala a sistemului!
    start /wait python_installer.exe /quiet InstallAllUsers=0 PrependPath=0 Include_test=0
    del python_installer.exe
    echo   -^> [SUCCES] Python 3.11 a fost instalat izolat!
) ELSE (
    echo   -^> Python 3.11 este disponibil pe sistem.
)

echo.
echo [PAS 2/5] Verificam motorul AI Ollama...
ollama --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    color 0E
    echo   -^> Ollama nu a fost gasit. Il descarcam si instalam...
    curl -L "https://ollama.com/download/OllamaSetup.exe" -o "OllamaSetup.exe"
    start /wait OllamaSetup.exe /S
    del OllamaSetup.exe
    echo   -^> [SUCCES] Ollama a fost instalat!
) ELSE (
    echo   -^> Ollama este deja instalat.
)

echo.
echo [PAS 3/5] Verificam mediul virtual izolat...
IF NOT EXIST ".venv\Scripts\activate.bat" (
    echo   -^> Cream mediul izolat STRICT cu Python 3.11...
    py -3.11 -m venv .venv
) ELSE (
    echo   -^> Mediul virtual exista deja.
)

call .venv\Scripts\activate.bat

echo.
echo [PAS 4/5] Verificam si instalam librariile necesare...
python -m pip install --upgrade pip --quiet
echo   -^> Instalam motorul OCR Paddle...
python -m pip install paddlepaddle --prefer-binary --quiet
echo   -^> Instalam restul dependentelor, poate dura un minut...
python -m pip install -r requirements.txt --prefer-binary --quiet

echo.
echo [PAS 5/5] Verificam inteligenta artificiala MedGemma...
ollama list | findstr "medgemma-1.5-4b-it-gguf:Q4_0" >nul
IF %ERRORLEVEL% NEQ 0 (
    echo   -^> Descarcam modelul medical de 2.8 GB...
    ollama pull hf.co/gguf-org/medgemma-1.5-4b-it-gguf:Q4_0
) ELSE (
    echo   -^> Modelul MedGemma este deja descarcat si pregatit!
)

echo.
color 0A
echo =========================================================
echo      Sistemul este pregatit! Pornim platforma...
echo =========================================================
streamlit run src/frontend/interfata.py
pause