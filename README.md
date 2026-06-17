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

## 3. Instalare și Rulare (Instrucțiuni pentru Utilizator)

Aplicația este concepută pentru a fi de tip "Plug & Play", configurându-se automat fără a necesita cunoștințe tehnice avansate din partea utilizatorului. 

**Pregătire inițială:**
* Descărcați întregul folder al aplicației pe calculatorul dumneavoastră și dezarhivați-l (dacă este în format ZIP).
* Asigurați-vă că aveți o conexiune stabilă la internet (necesară doar la prima rulare pentru descărcarea modelelor AI).

### 🪟 Pentru utilizatorii de Windows:
1. Intrați în folderul principal al proiectului.
2. Dați dublu-click pe fișierul **`Start_Medicode.bat`**.
3. **Gata!** La prima rulare, o fereastră neagră va apărea pe ecran și va instala automat tot sistemul (Python, motorul local AI Ollama și va descărca modelul medical securizat MedGemma de 2.8 GB). Acest proces poate dura câteva minute.
4. Odată finalizat, aplicația MEDICODE se va deschide automat în browserul dumneavoastră web.

### 🍏🐧 Pentru utilizatorii de macOS / Linux:
1. Deschideți aplicația **Terminal** și navigați către folderul principal al proiectului (ex: `cd /Calea/Catre/Medicode`).
2. Oferiți permisiunea de rulare a scriptului de instalare tastând această comandă (necesar doar o singură dată):
```bash
   chmod +x Start_Medicode.sh
   ```
3. Porniți aplicația tastând:
```bash
   ./Start_Medicode.sh
   ```
4. Sistemul va configura automat mediul și va descărca fișierele necesare, după care platforma se va deschide direct în browser.

*(Notă: Pentru a opri aplicația, trebuie doar să închideți fereastra terminalului pe care scrie "MEDICODE" sau să apăsați tastele `CTRL+C` în interiorul acelui terminal).*