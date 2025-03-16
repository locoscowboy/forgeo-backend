# Assurez-vous d'ajuster seulement les références à date_created/date_completed par created_at/updated_at
# Par exemple, dans la méthode run_audit, remplacez:
#   audit.date_completed = datetime.utcnow()
# par:
#   audit.updated_at = datetime.utcnow()

# Le reste du fichier reste identique
