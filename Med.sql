-- Supprimer la base de données si elle existe déjà


-- Création de la base de données
CREATE DATABASE Med;
USE Med;

-- Création de la table utilisateurs
CREATE TABLE utilisateurs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nom VARCHAR(100),
    email VARCHAR(100) UNIQUE,
    mot_de_passe VARCHAR(255),
    role ENUM('medecin', 'patient', 'administrateur'),
    numero_licence VARCHAR(50),  -- Applicable uniquement pour les médecins
    numero_assurance VARCHAR(50) -- Applicable uniquement pour les patients
);

-- Création de la table patients
CREATE TABLE patients (
    id INT AUTO_INCREMENT PRIMARY KEY,
    utilisateur_id INT NULL,
    date_naissance DATE NULL,
    adresse VARCHAR(255)NULL,
    numero_telephone VARCHAR(20)NULL,
    groupe_sanguin VARCHAR(5)NULL,
    FOREIGN KEY (utilisateur_id) REFERENCES utilisateurs(id)  ON DELETE CASCADE
);
 ON DELETE CASCADE

-- Création de la table medecins
CREATE TABLE medecins (
    id INT AUTO_INCREMENT PRIMARY KEY,
    utilisateur_id INT,
    specialite VARCHAR(100),
    numero_licence VARCHAR(50),
    FOREIGN KEY (utilisateur_id) REFERENCES utilisateurs(id)
);

-- Création de la table administration
CREATE TABLE administration (
    id INT AUTO_INCREMENT PRIMARY KEY,
    utilisateur_id INT,
    role_administratif VARCHAR(100),
    FOREIGN KEY (utilisateur_id) REFERENCES utilisateurs(id)
);

-- Création de la table dossiers_medicaux
CREATE TABLE dossiers_medicaux (
    id INT AUTO_INCREMENT PRIMARY KEY,
    patient_id INT NOT NULL,
    nom_prenom VARCHAR(200),
    date_naissance DATE,
    genre ENUM('masculin', 'feminin', 'autre'),
    
    coordonnees TEXT,
    numero_assurance VARCHAR(50),
    FOREIGN KEY (patient_id) REFERENCES utilisateurs(id)
);

-- Création de la table antecedents_medicaux
CREATE TABLE antecedents_medicaux (
    id INT AUTO_INCREMENT PRIMARY KEY,
    dossier_id INT NOT NULL,
    diagnostique TEXT,
    traitement TEXT,
    medecin_traitant INT,
    debut_maladie DATE,
    fin_maladie DATE,
    FOREIGN KEY (dossier_id) REFERENCES dossiers_medicaux(id),
    FOREIGN KEY (medecin_traitant) REFERENCES utilisateurs(id)
);

-- Création de la table visites_medicaux
CREATE TABLE visites_medicaux (
    id INT AUTO_INCREMENT PRIMARY KEY,
    dossier_id INT NOT NULL,
    etablissement_visite VARCHAR(100),
    medecin_id INT NOT NULL,
    date_visite DATE,
    diagnostique TEXT,
    traitement TEXT,
    resume_visite TEXT,
    notes TEXT,
    FOREIGN KEY (dossier_id) REFERENCES dossiers_medicaux(id),
    FOREIGN KEY (medecin_id) REFERENCES utilisateurs(id)
);

-- Création de la table modifications_dossiers
CREATE TABLE modifications_dossiers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    dossier_id INT,
    utilisateur_id INT,
    date_modification TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    details_modification TEXT,
    FOREIGN KEY (dossier_id) REFERENCES dossiers_medicaux(id),
    FOREIGN KEY (utilisateur_id) REFERENCES utilisateurs(id)
);

-- Création de la table rendez_vous
CREATE TABLE rendez_vous (
    id INT AUTO_INCREMENT PRIMARY KEY,
    patient_id INT NOT NULL,
    medecin_id INT NOT NULL,
    date_rdv DATE NOT NULL,
    heure_rdv TIME NOT NULL,
    statut ENUM('en_attente', 'confirmé', 'refusé') DEFAULT 'en_attente',
    FOREIGN KEY (patient_id) REFERENCES utilisateurs(id),
    FOREIGN KEY (medecin_id) REFERENCES utilisateurs(id)
);

-- Création de la table sauvegardes_dossiers
CREATE TABLE sauvegardes_dossiers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    dossier_id INT,
    version_num INT,
    date_sauvegarde TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    contenu TEXT,
    FOREIGN KEY (dossier_id) REFERENCES dossiers_medicaux(id)
);

-- Création de la table prescriptions
CREATE TABLE prescriptions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    dossier_id INT NOT NULL,
    date_prescription DATE NOT NULL,
    description TEXT,
    medecin_id INT NOT NULL,
    FOREIGN KEY (dossier_id) REFERENCES dossiers_medicaux(id),
    FOREIGN KEY (medecin_id) REFERENCES utilisateurs(id)
);

-- Création du trigger pour insérer automatiquement dans les tables spécifiques en fonction du rôle
DELIMITER //

CREATE TRIGGER after_insert_utilisateur
AFTER INSERT ON utilisateurs
FOR EACH ROW
BEGIN
    -- Si le rôle est "patient"
    IF NEW.role = 'patient' THEN
        INSERT INTO patients (utilisateur_id) VALUES (NEW.id);
    
    -- Si le rôle est "medecin"
    ELSEIF NEW.role = 'medecin' THEN
        INSERT INTO medecins (utilisateur_id, numero_licence) VALUES (NEW.id, NEW.numero_licence);
    
    -- Si le rôle est "administrateur"
    ELSEIF NEW.role = 'administrateur' THEN
        INSERT INTO administration (utilisateur_id) VALUES (NEW.id);
    END IF;
END //

DELIMITER ;
DELIMITER //

CREATE TRIGGER create_dossier_medical_after_patient_insert
AFTER INSERT ON utilisateurs
FOR EACH ROW
BEGIN
    -- Vérifie si l'utilisateur est un patient
    IF NEW.role = 'patient' THEN
        INSERT INTO dossiers_medicaux (patient_id, nom_prenom, numero_assurance)
        VALUES (NEW.id, CONCAT(NEW.nom, ' ', NEW.prenom), NEW.numero_assurance);
    END IF;
END //

DELIMITER ;

DELIMITER //

CREATE TRIGGER update_dossier_medical
AFTER UPDATE ON utilisateurs
FOR EACH ROW
BEGIN
    -- Update the corresponding dossier_medical with the new information from patients and utilisateurs
    UPDATE dossiers_medicaux AS d
    JOIN patients AS p ON p.utilisateur_id = NEW.id
    SET d.nom_prenom = NEW.nom,
        d.coordonnees = CONCAT(p.adresse, ' - ', p.numero_telephone),
        d.date_naissance = p.date_naissance,
        d.genre = p.genre
    WHERE d.patient_id = NEW.id;
END //

DELIMITER ;

