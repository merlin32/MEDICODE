# Medicode - Platforma ta medicală

## 1. Prezentare Generală a Aplicației
**Medicode** este o interfață digitală integrată și modernă, concepută pentru a monitoriza, optimiza și gestiona starea de sănătate prin digitalizarea indicatorilor biometrici. Pornind de la analiza nevoilor pacienților (care semnalează frecvent oboseală cronică și dificultăți în gestionarea energiei), Medicode transformă datele medicale brute din analizele de laborator într-o analiză riguroasă de risc și recomandări personalizate de lifestyle.

Aplicația folosește o arhitectură decuplată de tip **Client-Server local**. Nucleul de procesare rulează discret în background pe o stivă bazată pe **Python**, utilizând o bază de date locală **SQLite** pentru asigurarea confidențialității și istoricului datelor.

### Componente și Funcționalități Cheie
* **Modul de Încărcare și Parsare (Data Ingestion):** Suportă încărcarea fișierelor PDF și a imaginilor cu analize. Procesul de extragere este realizat automat printr-un **apel API (API call)** dedicat, care izolează elementele cheie: numele biomarkerului, valoarea măsurată, unitatea de măsură și intervalul de referință (min/max).
* **Sistem de Analiză și Agentic AI:** Identifică abaterile procentuale față de intervalul optim. Un prim model LLM evaluează riscurile și potențialele afecțiuni, iar un al doilea LLM preia diagnosticul pentru a formula sfaturi personalizate de lifestyle și vitalitate.
* **Gestiune și Istoric Local:** Corelează evoluția biomarkerilor în timp prin tabele și grafice interactive, fără a duplica înregistrările existente în baza de date.
* **Interfață Grafică Modernă (GUI):** Un mediu vizual prietenos organizat pe secțiuni clare, menit să ascundă complexitatea tehnică din backend.

---

## 2. Modul de Operare al Aplicației

Modul de operare al ecosistemului Medicode este împărțit în trei mari piloni funcționali: configurarea inițială, fluxul de procesare a analizelor și interacțiunea cu dashboard-ul de monitorizare.

### A. Configurarea Contului și Profilul Medical
1. **Crearea contului:** La prima interacțiune, utilizatorul își configurează profilul și este obligat să menționeze afecțiunile medicale preexistente. Sistemul caută afecțiunile în baza de date, le adaugă pe cele noi dacă nu există și le asociază contului ca fiind active.
2. **Gestionarea Profilului ("Profilul Meu"):** Secțiune dedicată în interfață unde utilizatorul poate edita oricând starea afecțiunilor sale, clasificându-le în **"Actuale"** sau **"Vindecate"**.

### B. Fluxul de Încărcare și Procesare a Analizelor
1. **Introducere Date Contextuale:** Atunci când încarcă analize, utilizatorul completează obligatoriu **Greutatea** și **Înălțimea** actuale (pentru calcularea automată a Indicelui de Masă Corporală - IMC) și selectează sau introduce **Clinica** unde a efectuat analizele.
2. **Extragerea și Normalizarea Datelor via API:**
   * Sistemul transmite documentul încărcat către o componentă externă printr-un **apel API (API call)**, care returnează parametrii izolați: `nume_biomarker`, `val_mas`, `unit_mas`, `ref_max`, `ref_min`.
   * *Notă*: Pentru intervalele de tip DA/NU, valorile de referință devin binarizate (DA → 1, NU → 0).
3. **Evaluarea Datelor Extrase:** Înainte de salvare, aplicația verifică duplicatele pentru a nu reintroduce biomarkeri identici. Ulterior, calculează automat **abaterea procentuală** față de limite și activează o variabilă de tip alertă (`true`/`false`) în cazul valorilor anormale.
4. **Interogarea Agentului AI:** Datele extrase, împreună cu alertele și abaterile calculate, sunt trimise către agentul AI. Afecțiunile detectate de AI sunt salvate în baza de date și asociate automat profilului utilizatorului.

### C. Monitorizare, Alerte și Raportare
* **Dashboard-ul Interactiv:** Afișează istoricul cronologic al sesiunilor de analize și evoluția biomarkerilor prin grafice de trend.
* **Sistemul de Alerte Vizuale:** Semnalizează instant fluctuațiile critice dintre sesiuni (de exemplu: o scădere drastică în greutate sau un biomarker care trece brusc din zona sigură în zona roșie de risc).
* **Generarea de Rapoarte:** Aplicația livrează un raport vizual (pentru pacient), simplificat, axat pe lifestyle și recomandări.

---

## 3. Instalare și Rulare Automată (Cross-Platform)

Procesul de instalare este complet automatizat prin scripturi inteligente de bootstrapping care asigură o **izolare totală a dependențelor**. Configurația curentă nu modifică și nu corupe versiunile globale de Python existente pe mașina ta de dezvoltare (ex: Python 3.13 / 3.14 fiind protejate complet).

### 🪟 Pentru utilizatorii de Windows (`Start_Medicode.bat`)

1. Deschideți directorul rădăcină al proiectului `MEDICODE`.
2. Executați cu dublu-click fișierul **`Start_Medicode.bat`**.
3. **Fluxul pas cu pas executat în mod automat de către script:**
   * **Pasul 1 (Verificare Python 3.11):** Verifică existența runtime-ului nativ compatibil Python 3.11. Dacă lipsește sau există o versiune experimentală mai nouă global, scriptul descarcă automat (`curl`) și instalează controlat versiunea corectă folosind parametrul `PrependPath=0` (astfel Python 3.11 rămâne izolat în proiect și nu suprascrie versiunea ta globală).
   * **Pasul 2 (Verificare Ollama):** Detectează dacă motorul AI local Ollama este instalat în sistem. În caz contrar, realizează descărcarea și instalarea automată.
   * **Pasul 3 (Inițializare Mediu Virtual):** Inițializează un mediu virtual local `.venv` asociat strict cu interpretorul Python 3.11, prevenind coliziunile globale.
   * **Pasul 4 (Instalare Dependențe):** Actualizează managerul de pachete `pip` în mod silențios, instalează automat motorul OCR local (`paddlepaddle` cu flag-ul `--prefer-binary` pentru a elimina cerința de compilatoare C++ externe sau erori GCC) și restul librăriilor menționate în `requirements.txt`.
   * **Pasul 5 (Pull Model AI):** Verifică în registrul Ollama prezența modelului medical calibrat `medgemma-1.5-4b-it-gguf:Q4_0`. Dacă acesta nu este stocat local, inițiază descărcarea automată (2.8 GB).
4. Aplicația va porni automat serverul local Streamlit și va deschide interfața securizată direct în browser la adresa `http://localhost:8501`.

### 🍏🐧 Pentru utilizatorii de macOS / Linux (`Start_Medicode.sh`)

1. Deschideți o instanță de Terminal în folderul proiectului.
2. Acordați permisiuni de execuție scriptului shell:
   ```bash
   chmod +x Start_Medicode.sh
3. Lansați executabilul:
   ```bash
   ./Start_Medicode.sh
4. Scriptul Unix va asigura detectarea automată a aplicației și componentelor Ollama, crearea spațiului .venv și pornirea instanței web Streamlit.

*(Notă: Pentru a opri aplicația, închideți fereastra terminalului sau apăsați tastele CTRL+C în interiorul acestuia.)*
## 4. Dezinstalare și Curățare Completă (Wizard Interactiv)

Pentru a asigura o mentenanță riguroasă a spațiului de stocare local și a dependențelor de sistem, platforma integrează scripturi avansate de eliminare granulară controlată.

### 🪟 Pentru utilizatorii de Windows (`Uninstall_Medicode.bat`)

Executarea fișierului deschide un utilitar securizat tip Wizard care funcționează pe baza unui principiu non-destructiv implicit, solicitând decizii explicite (`Y/N`) din partea utilizatorului pentru fiecare tip de date în parte:

1. **Opțiunea 1: Ștergerea fișierelor aplicației (.venv) și a modelului AI**
   * Șterge folderul local `.venv` cu toate bibliotecile atașate.
   * Apelează API-ul Ollama pentru a elimina definitiv modelul medical local (`medgemma`), eliberând instantaneu ~2.8 GB pe disc.
2. **Opțiunea 2: Ștergerea bazei de date locale (MEDICODE.db)**
   * Elimină complet directorul de stocare `data/database/`, curățând în siguranță istoricul analizelor medicale, datele pacientului și tabelele relaționale. Păstrarea bazei de date este recomandată implicit dacă doriți doar să actualizați codul aplicației fără a pierde istoricul clinic.
3. **Opțiunea 3: Dezinstalarea motorului AI Ollama**
   * Închide în siguranță procesele active din fundal (`ollama.exe`, `ollama app.exe`) pentru a evita blocarea fișierelor la ștergere.
   * Rulează un algoritm de detecție multi-cale (verifică Registry, AppData, Program Files și utilizează utilitarul nativ Microsoft `winget`) pentru a lansa dezinstalarea automată silențioasă a instanței Ollama globale de pe mașină.
4. **Opțiunea 4: Dezinstalarea Python 3.11**
   * Identifică ID-ul pachetului izolat Python 3.11 prin intermediul `winget` și realizează eliminarea sa curată din sistem, lăsând versiunile tale principale de dezvoltare (ex: Python 3.14) complet neatinse și perfect funcționale.

### 🍏🐧 Pentru utilizatorii de macOS / Linux (`Uninstall_Medicode.sh`)

1. Deschideți un terminal în folderul rădăcină al aplicației.
2. Oferiți drepturi de rulare utilitarului Unix cleanup:
   ```bash
   chmod +x Uninstall_Medicode.sh
3. Porniți procesul de curățare executând:
   ```bash
   ./Uninstall_Medicode.sh
4. Scriptul va opri execuția proceselor legate de aplicație, va elimina modular structura folderului virtual izolat .venv, va elibera cache-ul local și va șterge modelul medical stocat în Ollama, ghidându-vă interactiv prin pașii pe care doriți să îi confirmați.
5. După terminarea procesului, puteți șterge manual folderul aplicației în mod obișnuit (Move to Trash).