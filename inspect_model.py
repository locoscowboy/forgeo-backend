from app.models.audit import AuditResult
# Afficher la définition complète de la classe
print(AuditResult.__dict__)
# Afficher les noms des colonnes SQLAlchemy
print([c.name for c in AuditResult.__table__.columns])
