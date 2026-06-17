#!/bin/bash

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${RED}       AVERTISMENT DEZINSTALARE MEDICODE           ${NC}"

echo "Acest script va șterge:"
echo " 1. Mediul virtual izolat (.venv) și librăriile instalate."
echo " 2. Modelul medical AI (MedGemma - 2.8 GB) din sistem."
echo ""
echo "ATENȚIE: Python, Ollama și baza ta de date cu analize"
echo "NU vor fi șterse automat, pentru siguranța datelor tale."
echo ""

read -p "Ești sigur că vrei să continui? (Y/N): " choice
if [[ "$choice" != "Y" && "$choice" != "y" ]]; then
    echo "Operațiune anulată."
    exit 0
fi

echo -e "\n${YELLOW}[PAS 1/2] Ștergem modelul AI MedGemma din memoria Ollama...${NC}"
ollama rm hf.co/gguf-org/medgemma-1.5-4b-it-gguf:Q4_0

echo -e "${YELLOW}[PAS 2/2] Ștergem mediul virtual (.venv)...${NC}"
rm -rf .venv

echo -e "${GREEN} Dezinstalare finalizată cu succes!                ${NC}"
echo -e "${GREEN} Am eliberat spațiul de pe disc.                   ${NC}"
echo -e "${GREEN} Acum poți șterge întregul folder MEDICODE manual. ${NC}"
