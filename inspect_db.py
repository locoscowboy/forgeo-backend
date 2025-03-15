from sqlalchemy import inspect, create_engine
from sqlalchemy.orm import sessionmaker
import os

# Recréer la connexion manuellement
POSTGRES_USER = os.getenv("POSTGRES_USER", "forgeo")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "forgeo")
POSTGRES_SERVER = os.getenv("POSTGRES_SERVER", "db")
POSTGRES_DB = os.getenv("POSTGRES_DB", "forgeo")

SQLALCHEMY_DATABASE_URI = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_SERVER}/{POSTGRES_DB}"

engine = create_engine(SQLALCHEMY_DATABASE_URI)
inspector = inspect(engine)

# Afficher toutes les tables
print("Tables in the database:")
for table_name in inspector.get_table_names():
    print(f"- {table_name}")

# Si la table audits existe, afficher ses colonnes
if 'audits' in inspector.get_table_names():
    print("\nColonnes dans la table 'audits':")
    for column in inspector.get_columns('audits'):
        print(f"- {column['name']} (type: {column['type']})")
else:
    print("\nLa table 'audits' n'existe pas dans la base de données.")

# Vérifier si les autres tables d'audit existent
for table in ['audit_results', 'audit_detail_items']:
    if table in inspector.get_table_names():
        print(f"\nLa table '{table}' existe dans la base de données.")
    else:
        print(f"\nLa table '{table}' n'existe pas dans la base de données.")
