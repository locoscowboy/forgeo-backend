from sqlalchemy import create_engine, Column, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Recréer la connexion manuellement
POSTGRES_USER = os.getenv("POSTGRES_USER", "forgeo")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "forgeo")
POSTGRES_SERVER = os.getenv("POSTGRES_SERVER", "db")
POSTGRES_DB = os.getenv("POSTGRES_DB", "forgeo")

SQLALCHEMY_DATABASE_URI = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_SERVER}/{POSTGRES_DB}"

engine = create_engine(SQLALCHEMY_DATABASE_URI)
conn = engine.connect()

# Ajouter les colonnes manquantes
try:
    conn.execute("ALTER TABLE audits ADD COLUMN IF NOT EXISTS contacts_total INTEGER DEFAULT 0")
    conn.execute("ALTER TABLE audits ADD COLUMN IF NOT EXISTS companies_total INTEGER DEFAULT 0")
    conn.execute("ALTER TABLE audits ADD COLUMN IF NOT EXISTS deals_total INTEGER DEFAULT 0")
    print("Colonnes ajoutées avec succès!")
except Exception as e:
    print(f"Erreur lors de l'ajout des colonnes: {e}")
finally:
    conn.close()
