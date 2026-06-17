#!/bin/bash

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}     Pornire Sistem MEDICODE (Mac / Linux)         ${NC}"

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}[EROARE CRITICĂ] Python3 nu a fost găsit!${NC}"
    echo -e "Pe Mac: instalează Homebrew și rulează 'brew install python'"
    echo -e "Pe Linux: rulează 'sudo apt install python3 python3-venv'"
    exit 1
fi

if ! command -v ollama &> /dev/null; then
    echo -e "${YELLOW}[PAS 1/5] Motorul AI (Ollama) nu a fost găsit. Îl instalăm automat...${NC}"
    curl -fsSL https://ollama.com/install.sh | sh
    echo -e "${GREEN}[SUCCES] Ollama a fost instalat!${NC}\n"
else
    echo -e "${GREEN}[PAS 1/5] Ollama este deja instalat.${NC}"
fi

if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}[PAS 2/5] Creăm mediul izolat pentru aplicație...${NC}"
    python3 -m venv .venv
else
    echo -e "${GREEN}[PAS 2/5] Mediul virtual există deja.${NC}"
fi

echo -e "${YELLOW}[PAS 3/5] Activăm mediul și verificăm pachetele...${NC}"
source .venv/bin/activate

echo -e "${YELLOW}[PAS 4/5] Instalăm librăriile necesare (din requirements.txt)...${NC}"
python3 -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

echo -e "${YELLOW}[PAS 5/5] Verificăm modelul medical AI (MedGemma)...${NC}"
echo "Dacă este prima dată, va descărca fișierul (2.8 GB) și vei vedea progresul mai jos:"
ollama pull hf.co/gguf-org/medgemma-1.5-4b-it-gguf:Q4_0

echo -e "${GREEN}    Toate sistemele sunt funcționale!              ${NC}"
echo -e "${GREEN}    Lansăm platforma MEDICODE în browser...        ${NC}"
echo "Apasă CTRL+C în acest terminal când vrei să oprești aplicația."
echo ""

streamlit run src/frontend/interfata.py