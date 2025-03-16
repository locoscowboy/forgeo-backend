import os

# Lire le fichier original
with open('/app/app/api/v1/endpoints/audits.py', 'r') as file:
    content = file.read()

# Remplacer 'def run_audit' par 'async def run_audit'
if 'def run_audit' in content:
    content = content.replace('def run_audit', 'async def run_audit')
    
    # Écrire le fichier modifié
    with open('/app/app/api/v1/endpoints/audits.py', 'w') as file:
        file.write(content)
    print("Endpoint run_audit modifié avec succès pour être asynchrone!")
else:
    print("Fonction run_audit non trouvée dans le fichier")
