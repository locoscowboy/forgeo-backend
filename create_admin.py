from app.core.security import get_password_hash
from app.db.session import SessionLocal
from app.models.user import User
from sqlalchemy.orm import Session

def create_admin_user(db: Session) -> None:
    admin_user = db.query(User).filter(User.email == "admin@forgeo.io").first()
    if not admin_user:
        admin_user = User(
            email="admin@forgeo.io",
            hashed_password=get_password_hash("adminpassword"),
            is_superuser=True,
        )
        db.add(admin_user)
        db.commit()
        print("Admin user created successfully")
    else:
        print("Admin user already exists")

if __name__ == "__main__":
    db = SessionLocal()
    create_admin_user(db)
    db.close()
