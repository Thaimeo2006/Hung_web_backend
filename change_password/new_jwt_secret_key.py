import secrets

with open("password/jwt_secret_key.txt", "wb") as f:
    f.write(secrets.token_bytes(32))