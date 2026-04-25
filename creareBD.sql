-- Tabel Utilizatori
CREATE TABLE Utilizatori (
    id_utilizator INTEGER PRIMARY KEY AUTOINCREMENT,
    nume TEXT NOT NULL,
    prenume TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL CHECK (email LIKE '%@%')
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
    data_diagnostic TEXT,
    status TEXT, -- ex: 'Activ', 'Remisie'
    preexistent INTEGER NOT NULL DEFAULT 0 CHECK (preexistent IN (0, 1)),
    PRIMARY KEY (id_utilizator, nume_afectiune),
    FOREIGN KEY (id_utilizator) REFERENCES Utilizatori(id_utilizator) ON DELETE CASCADE,
    FOREIGN KEY (nume_afectiune) REFERENCES Afectiuni(nume_afectiune) ON DELETE CASCADE
);

-- Tabel Biomarkeri (Catalogul de Referință)
CREATE TABLE Biomarkeri (
    nume_biomarker TEXT PRIMARY KEY,
    unitate_masura TEXT,
    valoare_min_ref REAL,
    valoare_max_ref REAL
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
    id_valoare_mas INTEGER PRIMARY KEY AUTOINCREMENT,
    id_analiza INTEGER NOT NULL,
    nume_biomarker TEXT NOT NULL,
    valoare_masurata REAL NOT NULL,
    FOREIGN KEY (id_analiza) REFERENCES Analize(id_sesiune) ON DELETE CASCADE,
    FOREIGN KEY (nume_biomarker) REFERENCES Biomarkeri(nume_biomarker) ON DELETE RESTRICT
);

-- Indexare pentru rapiditatea interogărilor
CREATE INDEX idx_utilizatori_email ON Utilizatori(email);
CREATE INDEX idx_utilizatori_nume_prenume ON Utilizatori(nume, prenume);
CREATE INDEX idx_analize_utilizator ON Analize(id_utilizator);