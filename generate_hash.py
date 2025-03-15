import bcrypt

def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode(), salt)
    return hashed_password.decode()

if __name__ == "__main__":
    print(get_password_hash("adminpassword"))
