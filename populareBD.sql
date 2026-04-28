INSERT INTO Biomarkeri (nume_biomarker, sex, unitate_masura, valoare_min_ref, valoare_max_ref) VALUES
-- Hematologie
('Hemoglobină', 'M', 'g/dL', 13.5, 17.5),
('Hemoglobină', 'F', 'g/dL', 12.0, 15.5),
('Hematocrit', 'M', '%', 41.0, 50.0),
('Hematocrit', 'F', '%', 36.0, 46.0),
('Leucocite', 'I', '/µL', 4000, 10000),
('VSH', 'M', 'mm/h', 0, 15),
('VSH', 'F', 'mm/h', 0, 20),
-- Biochimie
('Glicemie', 'I', 'mg/dL', 70, 100),
('Creatinină', 'M', 'mg/dL', 0.7, 1.3),
('Creatinină', 'F', 'mg/dL', 0.6, 1.1),
('TGP', 'I', 'U/L', 0, 41),
('TGO', 'I', 'U/L', 0, 40),
('Colesterol Total', 'I', 'mg/dL', 120, 200),
('HDL', 'M', 'mg/dL', 40, 60),
('HDL', 'F', 'mg/dL', 50, 70),
('LDL', 'I', 'mg/dL', 0, 130),
('Trigliceride', 'I', 'mg/dL', 0, 150),
('Acid Uric seric', 'M', 'mg/dL', 3.4, 7.0),
('Acid Uric seric', 'F', 'mg/dL', 2.4, 5.7),
('Uree serică', 'I', 'mg/dL', 13, 43),
('Sideremie', 'M', 'µg/dL', 59, 158),
('Sideremie', 'F', 'µg/dL', 37, 145),
('Calciu ionic', 'I', 'mmol/L', 1.16, 1.32),
('Calciu seric', 'I', 'mg/dL', 8.6, 10.2),
('Bilirubină Totală', 'I', 'mg/dL', 0.1, 1.2),
-- Endocrinologie & Imunologie
('TSH', 'I', 'µIU/mL', 0.27, 4.2),
('FT4', 'I', 'ng/dL', 0.93, 1.7),
('IgA', 'I', 'mg/dL', 70, 400),
('IgG', 'I', 'mg/dL', 700, 1600),
('IgM', 'I', 'mg/dL', 40, 230),
('IgE', 'I', 'IU/mL', 0, 100),
-- Electroforeză
('Albumină (Electroforeză)', 'I', '%', 52, 65),
('Gama-globuline', 'I', '%', 10.7, 20.3);

-- Tabel Afectiuni (Catalog General)
INSERT INTO Afectiuni (nume_afectiune, descriere_generala) VALUES
('Anemie', 'Scăderea capacității sângelui de a transporta oxigen (Hb/Fier scăzut).'),
('Diabet Zaharat', 'Grup de boli metabolice caracterizate prin niveluri ridicate de glucoză în sânge.'),
('Dislipidemie', 'Dereglarea nivelului de grăsimi în sânge, factor de risc pentru ateroscleroză.'),
('Steatoză hepatică', 'Acumularea excesivă de grăsimi în celulele ficatului.'),
('Insuficiență renală', 'Scăderea capacității rinichilor de a filtra produșii de metabolism.'),
('Hipotiroidism', 'Activitate deficitară a glandei tiroide (TSH crescut).'),
('Hipertiroidism', 'Activitate excesivă a glandei tiroide (TSH scăzut).'),
('Sindrom Inflamator', 'Reacție biologică de apărare, indicată de VSH/Leucocite crescute.'),
('Sindrom Alergic', 'Reacție imunitară exagerată, indicată de IgE crescut.'),
('Poliglobulie', 'Creșterea patologică a numărului de hematii, risc de hipervâscozitate.'),
('Hemoragie Acută', 'Pierdere rapidă de volum sangvin, reflectată în scăderea bruscă a Hb/Ht.'),
('Deshidratare Severă', 'Scăderea volumului de plasmă, cauzând hemoconcentrație.'),
('Gută', 'Depunerea cristalelor de acid uric în articulații datorită hiperuricemiei.'),
('Sindrom Metabolic', 'Grup de factori de risc ce cresc probabilitatea de boli cardiace și diabet.'),
('Insuficiență Renală Acută', 'Deteriorarea rapidă și severă a funcției renale.'),
('Icter obstructiv / Colestază', 'Blocarea fluxului biliar, indicată de creșterea bilirubinei.'),
('Ciroză Hepatică', 'Stadiu avansat de fibroză a ficatului.'),
('Hepatită Alcoolică', 'Inflamație hepatică indusă de consumul de alcool.'),
('Hiperparatiroidism', 'Exces de PTH care duce la mobilizarea calciului în sânge.'),
('Hipocalcemie', 'Nivel scăzut de calciu, asociat cu deficit de Vitamina D.'),
('Mielom Multiplu', 'Cancer al celulelor plasmatice (vârf monoclonal pe electroforeză).'),
('Imunodeficiență Umorală', 'Capacitate scăzută de producție de anticorpi.'),
('Gamapatie Monoclonală', 'Prezența unei proteine anormale în sânge.'),
('Leucocitoză', 'Creșterea numărului de leucocite (infecție/inflamație).'),
('Leucopenie', 'Scăderea numărului de leucocite (risc de infecții).'),
('Risc Cardiovascular Crescut', 'Probabilitate ridicată de evenimente cardiace bazată pe profilul lipidic.'),
('Malnutriție / Malabsorbție', 'Deficiențe proteice sau de micronutrienți.');

-- Tabel Reguli_Diagnostic (SELECT e folosit pentru a obține id_biomarker corect)
INSERT INTO Reguli_Diagnostic (nume_afectiune, id_biomarker, directie_deviatie, pondere) VALUES

-- 1. Hematologie Extinsă & Inflamație (Completare)
('Anemie', (SELECT id_biomarker FROM Biomarkeri WHERE nume_biomarker='Sideremie' AND sex='M'), 'SCAZUT', 0.7),
('Anemie', (SELECT id_biomarker FROM Biomarkeri WHERE nume_biomarker='Sideremie' AND sex='F'), 'SCAZUT', 0.7),
('Anemie', (SELECT id_biomarker FROM Biomarkeri WHERE nume_biomarker='Hemoglobină' AND sex='M'), 'SCAZUT', 1.0),
('Anemie', (SELECT id_biomarker FROM Biomarkeri WHERE nume_biomarker='Hemoglobină' AND sex='F'), 'SCAZUT', 1.0),

('Poliglobulie', (SELECT id_biomarker FROM Biomarkeri WHERE nume_biomarker='Hemoglobină' AND sex='M'), 'CRESCUT', 0.9),
('Poliglobulie', (SELECT id_biomarker FROM Biomarkeri WHERE nume_biomarker='Hematocrit' AND sex='M'), 'CRESCUT', 1.0),
('Hemoragie Acută', (SELECT id_biomarker FROM Biomarkeri WHERE nume_biomarker='Hemoglobină' AND sex='F'), 'SCAZUT', 1.0),
('Sindrom Inflamator', (SELECT id_biomarker FROM Biomarkeri WHERE nume_biomarker='VSH' AND sex='F'), 'CRESCUT', 0.9),
('Sindrom Inflamator', (SELECT id_biomarker FROM Biomarkeri WHERE nume_biomarker='VSH' AND sex='M'), 'CRESCUT', 0.9),
('Sindrom Inflamator', (SELECT id_biomarker FROM Biomarkeri WHERE nume_biomarker='Leucocite'), 'CRESCUT', 0.7),
('Leucocitoză', (SELECT id_biomarker FROM Biomarkeri WHERE nume_biomarker='Leucocite'), 'CRESCUT', 1.0),
('Leucopenie', (SELECT id_biomarker FROM Biomarkeri WHERE nume_biomarker='Leucocite'), 'SCAZUT', 1.0),

-- 2. Profil Lipid & Risc Cardiovascular
('Dislipidemie', (SELECT id_biomarker FROM Biomarkeri WHERE nume_biomarker='LDL'), 'CRESCUT', 1.0),
('Dislipidemie', (SELECT id_biomarker FROM Biomarkeri WHERE nume_biomarker='Colesterol Total'), 'CRESCUT', 0.8),
('Dislipidemie', (SELECT id_biomarker FROM Biomarkeri WHERE nume_biomarker='Trigliceride'), 'CRESCUT', 0.7),
('Dislipidemie', (SELECT id_biomarker FROM Biomarkeri WHERE nume_biomarker='HDL' AND sex='M'), 'SCAZUT', 0.5),
('Dislipidemie', (SELECT id_biomarker FROM Biomarkeri WHERE nume_biomarker='HDL' AND sex='F'), 'SCAZUT', 0.5),
('Risc Cardiovascular Crescut', (SELECT id_biomarker FROM Biomarkeri WHERE nume_biomarker='LDL'), 'CRESCUT', 1.0),
('Risc Cardiovascular Crescut', (SELECT id_biomarker FROM Biomarkeri WHERE nume_biomarker='HDL' AND sex='F'), 'SCAZUT', 0.8),
('Sindrom Metabolic', (SELECT id_biomarker FROM Biomarkeri WHERE nume_biomarker='Trigliceride'), 'CRESCUT', 0.7),
('Sindrom Metabolic', (SELECT id_biomarker FROM Biomarkeri WHERE nume_biomarker='HDL' AND sex='M'), 'SCAZUT', 0.5),
-- 3. Funcție Hepatică & Malnutriție
('Steatoză hepatică', (SELECT id_biomarker FROM Biomarkeri WHERE nume_biomarker='TGP'), 'CRESCUT', 1.0),
('Steatoză hepatică', (SELECT id_biomarker FROM Biomarkeri WHERE nume_biomarker='TGO'), 'CRESCUT', 0.8),
('Steatoză hepatică', (SELECT id_biomarker FROM Biomarkeri WHERE nume_biomarker='Trigliceride'), 'CRESCUT', 0.5),
('Hepatită Alcoolică', (SELECT id_biomarker FROM Biomarkeri WHERE nume_biomarker='TGO'), 'CRESCUT', 0.9),
('Hepatită Alcoolică', (SELECT id_biomarker FROM Biomarkeri WHERE nume_biomarker='TGP'), 'CRESCUT', 0.5),
('Icter obstructiv / Colestază', (SELECT id_biomarker FROM Biomarkeri WHERE nume_biomarker='Bilirubină Totală'), 'CRESCUT', 1.0),
('Ciroză Hepatică', (SELECT id_biomarker FROM Biomarkeri WHERE nume_biomarker='Bilirubină Totală'), 'CRESCUT', 0.7),
('Ciroză Hepatică', (SELECT id_biomarker FROM Biomarkeri WHERE nume_biomarker='Albumină (Electroforeză)'), 'SCAZUT', 0.8),
('Malnutriție / Malabsorbție', (SELECT id_biomarker FROM Biomarkeri WHERE nume_biomarker='Albumină (Electroforeză)'), 'SCAZUT', 1.0),
('Malnutriție / Malabsorbție', (SELECT id_biomarker FROM Biomarkeri WHERE nume_biomarker='Uree serică'), 'SCAZUT', 0.6),

-- 4. Funcție Renală & Guta
('Insuficiență renală', (SELECT id_biomarker FROM Biomarkeri WHERE nume_biomarker='Creatinină' AND sex='M'), 'CRESCUT', 1.0),
('Insuficiență renală', (SELECT id_biomarker FROM Biomarkeri WHERE nume_biomarker='Creatinină' AND sex='F'), 'CRESCUT', 1.0),
('Insuficiență renală', (SELECT id_biomarker FROM Biomarkeri WHERE nume_biomarker='Uree serică'), 'CRESCUT', 0.9),
('Insuficiență renală', (SELECT id_biomarker FROM Biomarkeri WHERE nume_biomarker='Acid Uric seric' AND sex='M'), 'CRESCUT', 0.6),
('Insuficiență Renală Acută', (SELECT id_biomarker FROM Biomarkeri WHERE nume_biomarker='Creatinină' AND sex='M'), 'CRESCUT', 1.0),
('Deshidratare Severă', (SELECT id_biomarker FROM Biomarkeri WHERE nume_biomarker='Uree serică'), 'CRESCUT', 0.8),
('Deshidratare Severă', (SELECT id_biomarker FROM Biomarkeri WHERE nume_biomarker='Hematocrit' AND sex='M'), 'CRESCUT', 0.6),
('Gută', (SELECT id_biomarker FROM Biomarkeri WHERE nume_biomarker='Acid Uric seric' AND sex='M'), 'CRESCUT', 1.0),
('Gută', (SELECT id_biomarker FROM Biomarkeri WHERE nume_biomarker='Acid Uric seric' AND sex='F'), 'CRESCUT', 1.0),

-- 5. Endocrinologie (Tiroidă & Calciu)
('Hipotiroidism', (SELECT id_biomarker FROM Biomarkeri WHERE nume_biomarker='FT4'), 'SCAZUT', 0.9),
('Hipertiroidism', (SELECT id_biomarker FROM Biomarkeri WHERE nume_biomarker='FT4'), 'CRESCUT', 0.9),
('Hiperparatiroidism', (SELECT id_biomarker FROM Biomarkeri WHERE nume_biomarker='Calciu seric'), 'CRESCUT', 1.0),
('Hiperparatiroidism', (SELECT id_biomarker FROM Biomarkeri WHERE nume_biomarker='Calciu ionic'), 'CRESCUT', 0.9),
('Hipocalcemie', (SELECT id_biomarker FROM Biomarkeri WHERE nume_biomarker='Calciu seric'), 'SCAZUT', 1.0),

-- 6. Imunologie & Oncologie (Electroforeză)
('Sindrom Alergic', (SELECT id_biomarker FROM Biomarkeri WHERE nume_biomarker='IgE'), 'CRESCUT', 1.0),
('Mielom Multiplu', (SELECT id_biomarker FROM Biomarkeri WHERE nume_biomarker='Gama-globuline'), 'CRESCUT', 0.9),
('Mielom Multiplu', (SELECT id_biomarker FROM Biomarkeri WHERE nume_biomarker='IgG'), 'CRESCUT', 0.7),
('Imunodeficiență Umorală', (SELECT id_biomarker FROM Biomarkeri WHERE nume_biomarker='IgG'), 'SCAZUT', 1.0),
('Imunodeficiență Umorală', (SELECT id_biomarker FROM Biomarkeri WHERE nume_biomarker='IgA'), 'SCAZUT', 0.8),
('Imunodeficiență Umorală', (SELECT id_biomarker FROM Biomarkeri WHERE nume_biomarker='IgM'), 'SCAZUT', 0.8),
('Gamapatie Monoclonală', (SELECT id_biomarker FROM Biomarkeri WHERE nume_biomarker='Gama-globuline'), 'CRESCUT', 1.0);


INSERT INTO Utilizatori (cnp, 
nume, prenume, email, sex, data_nasterii, parola_hash) VALUES
    ('1850520123456', 'Popescu', 'Ion', 'ion.popescu@gmail.com', 'M', '1985-05-20','test1'),
    ('2920315678901', 'Ionescu', 'Maria', 'maria.ionescu@gmail.com', 'F', '1992-03-15','test2'),
    ('1781102234567', 'Dumitru', 'Andrei', 'andrei.d@gmail.com', 'M', '1978-11-02','test3'),
    ('2000725345678', 'Constantin', 'Elena', 'elena.c@gmail.com', 'F', '2000-07-25','test4'),
    ('1950110456789', 'Radu', 'Mihai', 'mihai.radu@gmail.com', 'M', '1995-01-10','test5');

INSERT INTO Analize (id_utilizator, data_recoltare, tip_sesiune) VALUES
    (1, '2024-01-15', 'Sânge'),
    (1, '2024-01-15', 'Sânge'),

    (2, '2024-02-10', 'Sânge'),
    (2, '2024-02-12', 'Sânge'),

    (3, '2024-03-05', 'Sânge');

INSERT INTO Valori_Masurate (id_analiza, id_biomarker, valoare_masurata) VALUES
    -- Sesiunea 1 (Utilizator 1 - Masculin): Hemoglobină, Glicemie, TSH
    (1, 1, 14.2),  -- Hemoglobină M (Normal)
    (1, 8, 115.0), -- Glicemie I (Peste limita de 100) -> ALERTĂ
    (1, 26, 3.1),  -- TSH I (Normal)

    -- Sesiunea 2 (Utilizator 1 - Masculin): Creatinină, LDL, VSH
    (2, 9, 1.5),   -- Creatinină M (Peste limita de 1.3) -> ALERTĂ
    (2, 16, 110.0),-- LDL I (Normal)
    (2, 6, 8.0),   -- VSH M (Normal)

    -- Sesiunea 3 (Utilizator 2 - Feminin): Hemoglobină, Calciu seric, TGP
    (3, 2, 11.5),  -- Hemoglobină F (Sub limita de 12) -> ALERTĂ
    (3, 24, 9.2),  -- Calciu seric I (Normal)
    (3, 11, 35.0), -- TGP I (Normal)

    -- Sesiunea 4 (Utilizator 2 - Feminin): Colesterol Total, HDL, Trigliceride
    (4, 13, 210.0),-- Colesterol Total I (Peste limita de 200) -> ALERTĂ
    (4, 15, 55.0), -- HDL F (Normal)
    (4, 17, 140.0),-- Trigliceride I (Normal)

    -- Sesiunea 5 (Utilizator 3 - Masculin): Hematocrit, Acid Uric, VSH
    (5, 3, 45.0),  -- Hematocrit M (Normal)
    (5, 18, 7.5),  -- Acid Uric M (Peste limita de 7) -> ALERTĂ
    (5, 6, 25.0);  -- VSH M (Peste limita de 15) -> ALERTĂ
