import os

# Lire le fichier original
with open('/app/app/api/v1/endpoints/audits.py', 'r') as file:
    content = file.read()

# Repérer la fonction run_audit et la remplacer par une version corrigée
if 'async def run_audit' in content:
    # Trouver le début et la fin de la fonction
    start_index = content.find('async def run_audit')
    end_marker = '        audit_service = HubspotAuditService(db, current_user.id)'
    end_index = content.find(end_marker, start_index)
    
    if end_index > -1:
        # Récupérer la partie avant la fonction
        before_function = content[:start_index]
        
        # Trouver où commence la fonction suivante
        next_function_start = content.find('@router', end_index)
        if next_function_start == -1:
            next_function_start = len(content)
        
        # Récupérer la partie après la fonction
        after_function = content[next_function_start:]
        
        # Nouvelle implémentation améliorée
        new_implementation = '''async def run_audit(
    *,
    db: Session = Depends(deps.get_db),
    id: int,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Exécute manuellement un audit HubSpot existant.
    """
    audit = crud.get_audit(db, id=id)
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")
    if audit.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Vérifier que l'utilisateur a un token HubSpot actif
    token = crud.crud_hubspot.get_active_token(db, current_user.id)
    if not token:
        raise HTTPException(
            status_code=400,
            detail="No active HubSpot integration found."
        )
    
    try:
        # Réinitialiser le statut de l'audit si nécessaire
        if audit.status not in ["in_progress", "pending"]:
            crud.update_audit(db, db_obj=audit, obj_in={"status": "in_progress"})
        
        # Lancer l'audit directement (pas en tâche background)
        audit_service = HubspotAuditService(db, current_user.id)
        
        # Cette approche est sûre car FastAPI gère déjà les requêtes asynchrones
        # L'audit sera exécuté et les exceptions seront correctement gérées
        try:
            await audit_service.run_audit(audit.id)
            return audit
        except Exception as e:
            # Mettre à jour le statut en cas d'erreur
            audit.status = "failed"
            audit.updated_at = datetime.utcnow()
            db.add(audit)
            db.commit()
            raise HTTPException(status_code=500, detail=f"Audit failed: {str(e)}")
    except Exception as e:
        crud.update_audit(db, db_obj=audit, obj_in={"status": "failed"})
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
'''
        
        # Assembler le nouveau contenu
        new_content = before_function + new_implementation + after_function
        
        # Écrire le nouveau contenu
        with open('/app/app/api/v1/endpoints/audits.py', 'w') as file:
            file.write(new_content)
        
        print("Endpoint run_audit corrigé avec succès!")
    else:
        print("Structure de l'endpoint run_audit non reconnue")
else:
    print("Fonction async def run_audit non trouvée")
