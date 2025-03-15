import os

# Lire le fichier original
with open('/app/app/services/hubspot_audit.py', 'r') as file:
    content = file.read()

# Remplacer les références aux anciennes colonnes
content = content.replace('audit.date_completed = datetime.utcnow()', 'audit.updated_at = datetime.utcnow()')
content = content.replace('audit.date_created', 'audit.created_at')

# Écrire le fichier mis à jour
with open('/app/app/services/hubspot_audit.py', 'w') as file:
    file.write(content)

print("Service HubspotAudit mis à jour!")
