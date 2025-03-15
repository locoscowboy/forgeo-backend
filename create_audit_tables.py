from sqlalchemy import create_engine, text
import os

# Configuration de la connexion
POSTGRES_USER = os.getenv("POSTGRES_USER", "forgeo")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "forgeo")
POSTGRES_SERVER = os.getenv("POSTGRES_SERVER", "db")
POSTGRES_DB = os.getenv("POSTGRES_DB", "forgeo")

SQLALCHEMY_DATABASE_URI = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_SERVER}/{POSTGRES_DB}"

engine = create_engine(SQLALCHEMY_DATABASE_URI)

# SQL pour ajouter les colonnes à audits
add_columns_sql = """
ALTER TABLE audits ADD COLUMN IF NOT EXISTS contacts_total INTEGER DEFAULT 0;
ALTER TABLE audits ADD COLUMN IF NOT EXISTS companies_total INTEGER DEFAULT 0;
ALTER TABLE audits ADD COLUMN IF NOT EXISTS deals_total INTEGER DEFAULT 0;
"""

# SQL pour créer la table audit_results si elle n'existe pas
create_audit_results_sql = """
CREATE TABLE IF NOT EXISTS audit_results (
    id SERIAL PRIMARY KEY,
    audit_id INTEGER REFERENCES audits(id) ON DELETE CASCADE,
    category VARCHAR(50) NOT NULL,
    criterion VARCHAR(100) NOT NULL,
    field_name VARCHAR(100) NOT NULL,
    empty_count INTEGER DEFAULT 0,
    total_count INTEGER DEFAULT 0,
    percentage FLOAT DEFAULT 0.0
);
"""

# SQL pour créer la table audit_detail_items si elle n'existe pas
create_audit_details_sql = """
CREATE TABLE IF NOT EXISTS audit_detail_items (
    id SERIAL PRIMARY KEY,
    audit_id INTEGER REFERENCES audits(id) ON DELETE CASCADE,
    result_id INTEGER REFERENCES audit_results(id) ON DELETE CASCADE,
    category VARCHAR(50) NOT NULL,
    criterion VARCHAR(100) NOT NULL,
    hubspot_id VARCHAR(50) NOT NULL,
    object_data JSONB
);
"""

with engine.connect() as conn:
    try:
        # Exécuter dans une transaction
        with conn.begin():
            # Ajouter les colonnes à audits
            conn.execute(text(add_columns_sql))
            
            # Créer la table audit_results
            conn.execute(text(create_audit_results_sql))
            
            # Créer la table audit_detail_items
            conn.execute(text(create_audit_details_sql))
            
        print("Mise à jour de la base de données réussie!")
    except Exception as e:
        print(f"Erreur lors de la mise à jour de la base de données: {e}")
