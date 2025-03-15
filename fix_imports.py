import sys
import importlib

# Vider le cache des modules concernés
modules_to_reload = [
    'app.schemas.audit', 
    'app.schemas',
    'app.api.v1.endpoints.audits'
]

for module in modules_to_reload:
    if module in sys.modules:
        print(f"Recharging module {module}")
        importlib.reload(sys.modules[module])

# Vérifier que la classe AuditResultSummary est importable
try:
    from app.schemas.audit import AuditResultSummary
    print("AuditResultSummary importé avec succès!")
except ImportError as e:
    print(f"Erreur d'import: {e}")

print("Imports vérifiés et rechargés!")
