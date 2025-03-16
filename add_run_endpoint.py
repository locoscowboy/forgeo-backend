import os

# Lire le fichier original
with open('/app/app/api/v1/endpoints/audits.py', 'r') as file:
    content = file.read()

# Code de l'endpoint /run à ajouter
run_endpoint = """
@router.post("/{id}/run", response_model=schemas.Audit)
def run_audit(
    *,
    db: Session = Depends(deps.get_db),
    id: int,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    \"\"\"
    Exécute manuellement un audit HubSpot existant.
    \"\"\"
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
        
        # Lancer l'audit en arrière-plan
        audit_service = HubspotAuditService(db, current_user.id)
        asyncio.create_task(audit_service.run_audit(audit.id))
        
        return audit
    except Exception as e:
        crud.update_audit(db, db_obj=audit, obj_in={"status": "failed"})
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
"""

# Insérer l'endpoint avant l'endpoint des résultats
if '@router.get("/{id}/results"' in content:
    parts = content.split('@router.get("/{id}/results"')
    new_content = parts[0] + run_endpoint + '\n\n@router.get("/{id}/results"' + parts[1]
    with open('/app/app/api/v1/endpoints/audits.py', 'w') as file:
        file.write(new_content)
    print("Endpoint /run ajouté avec succès!")
else:
    print("Endpoint des résultats non trouvé")
