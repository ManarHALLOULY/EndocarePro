-- Initialize database schema for Endotrace medical device traceability system

-- Users table for role-based access control
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT CHECK(role IN ('admin', 'biomedical', 'sterilisation')) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Endoscope inventory table
CREATE TABLE IF NOT EXISTS endoscopes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    designation TEXT NOT NULL,
    marque TEXT NOT NULL,
    modele TEXT NOT NULL,
    numero_serie TEXT UNIQUE NOT NULL,
    etat TEXT CHECK(etat IN ('fonctionnel', 'en panne')) NOT NULL,
    observation TEXT,
    localisation TEXT NOT NULL,
    created_by TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Usage reports table for sterilization agents  
CREATE TABLE IF NOT EXISTS usage_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom_operateur TEXT NOT NULL,
    endoscope TEXT NOT NULL,
    numero_serie TEXT NOT NULL,
    medecin TEXT NOT NULL,
    etat TEXT CHECK(etat IN ('fonctionnel', 'en panne')) NOT NULL,
    nature_panne TEXT,
    date_utilisation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Enhanced sterilization reports table
CREATE TABLE IF NOT EXISTS sterilisation_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    -- Informations Générales
    nom_operateur TEXT NOT NULL,
    endoscope TEXT NOT NULL,
    numero_serie TEXT NOT NULL,
    medecin_responsable TEXT NOT NULL,
    
    -- Désinfection
    date_desinfection DATE NOT NULL,
    type_desinfection TEXT CHECK(type_desinfection IN ('manuel', 'automatique')) NOT NULL,
    cycle TEXT CHECK(cycle IN ('complet', 'incomplet')) NOT NULL,
    test_etancheite TEXT CHECK(test_etancheite IN ('réussi', 'échoué')) NOT NULL,
    heure_debut TIME NOT NULL,
    heure_fin TIME NOT NULL,
    
    -- Procédure Médicale
    procedure_medicale TEXT NOT NULL,
    salle TEXT NOT NULL,
    type_acte TEXT NOT NULL,
    
    -- État d'utilisation
    etat_endoscope TEXT CHECK(etat_endoscope IN ('fonctionnel', 'en panne')) NOT NULL,
    nature_panne TEXT,
    
    -- Métadonnées
    created_by TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default admin user
INSERT OR IGNORE INTO users (username, password, role) 
VALUES ('admin', 'admin123', 'admin');

-- Insert sample biomedical engineer
INSERT OR IGNORE INTO users (username, password, role) 
VALUES ('bio_eng', 'bio123', 'biomedical');

-- Insert sample sterilization agent
INSERT OR IGNORE INTO users (username, password, role) 
VALUES ('steril_agent', 'steril123', 'sterilisation');
