from app.crud.user import get, get_by_email, get_multi, create, update, remove, authenticate
# Import du module hubspot complet comme requis par hubspot_audit.py
from app.crud import hubspot as crud_hubspot
# Import des fonctions d'audit
from app.crud.crud_audit import (
    create_audit,
    get_audit,
    get_audits,
    update_audit,
    delete_audit,
    get_audit_results,
    get_audit_details
)
