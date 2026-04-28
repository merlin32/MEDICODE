--Stergere tabele
DROP INDEX IF EXISTS idx_analize_utilizator;
DROP INDEX IF EXISTS idx_utilizatori_nume_prenume;
DROP INDEX IF EXISTS idx_utilizatori_email;

DROP TABLE IF EXISTS Valori_Masurate;
DROP TABLE IF EXISTS Analize;
DROP TABLE IF EXISTS Utilizator_Afectiune;
DROP TABLE IF EXISTS Biomarkeri;
DROP TABLE IF EXISTS Afectiuni;
DROP TABLE IF EXISTS Utilizatori;
DROP TABLE IF EXISTS Reguli_Diagnostic;

-- Tabel Utilizatori
CREATE TABLE Utilizatori (
    id_utilizator INTEGER PRIMARY KEY AUTOINCREMENT,
    cnp TEXT UNIQUE NOT NULL CHECK (length(cnp) = 13 AND cnp NOT GLOB '*[^0-9]*'),
    nume TEXT NOT NULL,
    prenume TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL CHECK (email LIKE '%@%'),
    sex TEXT NOT NULL CHECK (sex IN ('F', 'M')),
    data_nasterii DATE NOT NULL
);

-- Tabel Afectiuni (Catalogul General)
CREATE TABLE Afectiuni (
    nume_afectiune TEXT PRIMARY KEY,
    descriere_generala TEXT NOT NULL
);

-- Tabel Asociativ: Utilizator_Afectiune (Relație M-M)
CREATE TABLE Utilizator_Afectiune (
    id_utilizator INTEGER NOT NULL,
    nume_afectiune TEXT NOT NULL,
    data_diagnostic TEXT NOT NULL,
    status TEXT, -- ex: 'Activ', 'Remisie'
    preexistent INTEGER NOT NULL DEFAULT 0 CHECK (preexistent IN (0, 1)),
    PRIMARY KEY (id_utilizator, nume_afectiune),
    FOREIGN KEY (id_utilizator) REFERENCES Utilizatori(id_utilizator) ON DELETE CASCADE,
    FOREIGN KEY (nume_afectiune) REFERENCES Afectiuni(nume_afectiune) ON DELETE CASCADE
);

-- Tabel Biomarkeri (Catalogul de Referință)
CREATE TABLE Biomarkeri (
    id_biomarker INTEGER PRIMARY KEY AUTOINCREMENT,
    nume_biomarker TEXT NOT NULL,
    sex TEXT CHECK (sex IN ('M', 'F', 'I')) NOT NULL, -- I = irelevant
    unitate_masura TEXT NOT NULL,
    valoare_min_ref REAL NOT NULL,
    valoare_max_ref REAL NOT NULL,
    UNIQUE(nume_biomarker, sex) -- nu pot exista mai multe perechi de tipul biomarker - sex
);

CREATE TABLE Reguli_Diagnostic (
    nume_afectiune TEXT NOT NULL,
    id_biomarker INTEGER NOT NULL,
    directie_deviatie TEXT CHECK (directie_deviatie IN ('SCAZUT', 'CRESCUT')) NOT NULL,
    pondere REAL DEFAULT 1.0, -- Cât de important e acest biomarker pentru boala respectivă
    PRIMARY KEY (nume_afectiune, id_biomarker),
    FOREIGN KEY (nume_afectiune) REFERENCES Afectiuni(nume_afectiune),
    FOREIGN KEY (id_biomarker) REFERENCES Biomarkeri(id_biomarker)
);

-- Tabel Analize (Sesiuni)
CREATE TABLE Analize (
    id_sesiune INTEGER PRIMARY KEY AUTOINCREMENT,
    id_utilizator INTEGER NOT NULL,
    data_recoltare TEXT NOT NULL CHECK (length(data_recoltare) >= 10),
    tip_sesiune TEXT NOT NULL CHECK (tip_sesiune IN ('Sânge', 'Urină', 'Coprocultură')),
    FOREIGN KEY (id_utilizator) REFERENCES Utilizatori(id_utilizator) ON DELETE CASCADE
);

-- Tabel Valori_Masurate
CREATE TABLE Valori_Masurate (
    id_analiza INTEGER NOT NULL,
    id_biomarker INTEGER NOT NULL,
    valoare_masurata REAL NOT NULL,
    PRIMARY KEY (id_analiza, id_biomarker),
    FOREIGN KEY (id_analiza) REFERENCES Analize(id_sesiune) ON DELETE CASCADE,
    FOREIGN KEY (id_biomarker) REFERENCES Biomarkeri(id_biomarker) ON DELETE RESTRICT
);

-- Indexare pentru rapiditatea interogărilor
CREATE INDEX idx_utilizatori_email ON Utilizatori(email);
CREATE INDEX idx_utilizatori_nume_prenume ON Utilizatori(nume, prenume);
CREATE INDEX idx_analize_utilizator ON Analize(id_utilizator);