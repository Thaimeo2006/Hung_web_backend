from database import SessionLocal, User
from passlib.context import CryptContext

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)

db = SessionLocal()
username = "test"
password = "test"

password_hash = pwd_context.hash(password)
user = User(
    username = username,
    password_hash = password_hash
)

db.add(user)
db.commit()

db.close()