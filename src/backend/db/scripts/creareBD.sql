--Stergere tabele
DROP INDEX IF EXISTS idx_analize_utilizator;
DROP INDEX IF EXISTS idx_utilizatori_nume_prenume;
DROP INDEX IF EXISTS idx_utilizatori_email;
DROP INDEX IF EXISTS idx_clinici_analize;

DROP TABLE IF EXISTS Valori_Masurate;
DROP TABLE IF EXISTS Analize;
DROP TABLE IF EXISTS Utilizator_Afectiune;
DROP TABLE IF EXISTS Biomarkeri;
DROP TABLE IF EXISTS Afectiuni;
DROP TABLE IF EXISTS Utilizatori;
DROP TABLE IF EXISTS Clinici;

-- Tabel Utilizatori
CREATE TABLE Utilizatori (
    id_utilizator INTEGER PRIMARY KEY AUTOINCREMENT,
    cnp TEXT UNIQUE NOT NULL CHECK (length(cnp) = 13 AND cnp NOT GLOB '*[^0-9]*'),
    nume TEXT NOT NULL,
    prenume TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL CHECK (email LIKE '%@%'),
    sex TEXT NOT NULL CHECK (sex IN ('F', 'M')),
    data_nasterii DATE NOT NULL,
    parola_hash TEXT NOT NULL
);

-- Tabel Analize (Sesiuni)
CREATE TABLE Analize (
    id_sesiune INTEGER PRIMARY KEY AUTOINCREMENT,
    id_utilizator INTEGER NOT NULL,
    id_clinica INTEGER NOT NULL,
    data_recoltare DATE NOT NULL,
    FOREIGN KEY (id_utilizator) REFERENCES Utilizatori(id_utilizator) ON DELETE CASCADE,
    FOREIGN KEY (id_clinica) REFERENCES Clinici(id_clinica)
);

--Tabel Clinici
CREATE TABLE Clinici (
    id_clinica INTEGER PRIMARY KEY AUTOINCREMENT,
    nume_clinica TEXT UNIQUE NOT NULL
);

-- Tabel Valori_Masurate
CREATE TABLE Valori_Masurate (
    id_sesiune INTEGER NOT NULL,
    id_biomarker INTEGER NOT NULL,
    val_mas REAL NOT NULL,
    unit_mas TEXT NOT NULL,
    PRIMARY KEY (id_sesiune, id_biomarker),
    FOREIGN KEY (id_sesiune) REFERENCES Analize(id_sesiune) ON DELETE CASCADE,
    FOREIGN KEY (id_biomarker) REFERENCES Biomarkeri(id_biomarker) ON DELETE RESTRICT
);

-- Tabel Biomarkeri (Catalogul de Referință)
CREATE TABLE Biomarkeri (
    id_biomarker INTEGER PRIMARY KEY AUTOINCREMENT,
    nume_biomarker TEXT NOT NULL,
    ref_max REAL NOT NULL,
    ref_min REAL NOT NULL,
    is_bool BOOLEAN NOT NULL
);

-- Tabel Asociativ: Utilizator_Afectiune (Relație M-M)
CREATE TABLE Utilizator_Afectiune (
    id_utilizator INTEGER NOT NULL,
    nume_afectiune TEXT NOT NULL,
    status TEXT, -- ex: 'Activ', 'Remisie'
    PRIMARY KEY (id_utilizator, nume_afectiune),
    FOREIGN KEY (id_utilizator) REFERENCES Utilizatori(id_utilizator) ON DELETE CASCADE,
    FOREIGN KEY (nume_afectiune) REFERENCES Afectiuni(nume_afectiune) ON DELETE CASCADE
);

-- Tabel Afectiuni (Catalogul General)
CREATE TABLE Afectiuni (
    nume_afectiune TEXT PRIMARY KEY,
    descriere_generala TEXT NOT NULL
);

-- Indexare pentru rapiditatea interogărilor
CREATE INDEX idx_utilizatori_email ON Utilizatori(email);
CREATE INDEX idx_utilizatori_nume_prenume ON Utilizatori(nume, prenume);
CREATE INDEX idx_analize_utilizator ON Analize(id_utilizator);
CREATE INDEX idx_clinici_analize ON Clinici(id_clinica);