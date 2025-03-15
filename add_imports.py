import os

# Lire le fichier original
with open('/app/app/api/v1/endpoints/audits.py', 'r') as file:
    content = file.read()

# Ajouter les imports nécessaires s'ils n'existent pas déjà
new_imports = """from typing import Any, List
import asyncio

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.api import deps
from app.models.user import User
from app.services.hubspot_audit import HubspotAuditService
"""

# Remplacer la section des imports
if 'from typing import Any, List' in content:
    # Trouver la fin des imports
    lines = content.split('\n')
    import_section_end = 0
    for i, line in enumerate(lines):
        if line.strip() == 'router = APIRouter()':
            import_section_end = i
            break
    
    if import_section_end > 0:
        # Remplacer la section des imports
        new_content = new_imports + '\n'.join(lines[import_section_end:])
        with open('/app/app/api/v1/endpoints/audits.py', 'w') as file:
            file.write(new_content)
        print("Imports ajoutés avec succès!")
    else:
        print("Structure du fichier non reconnue")
else:
    print("Section d'imports non trouvée")
