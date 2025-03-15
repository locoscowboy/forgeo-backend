import os

# Lire le fichier original
with open('/app/app/api/v1/endpoints/audits.py', 'r') as file:
    content = file.read()

# Vérifier si l'import de datetime existe déjà
if 'from datetime import datetime' not in content:
    # Ajouter l'import après les imports existants
    import_section_end = content.find('from app.services.hubspot_audit import HubspotAuditService')
    if import_section_end > -1:
        # Trouver la fin de la ligne
        line_end = content.find('\n', import_section_end)
        if line_end > -1:
            # Insérer l'import de datetime
            new_content = content[:line_end+1] + 'from datetime import datetime\n' + content[line_end+1:]
            
            # Écrire le nouveau contenu
            with open('/app/app/api/v1/endpoints/audits.py', 'w') as file:
                file.write(new_content)
            
            print("Import datetime ajouté avec succès!")
        else:
            print("Structure du fichier non reconnue")
    else:
        print("Section d'imports non trouvée")
else:
    print("Import datetime existe déjà")
