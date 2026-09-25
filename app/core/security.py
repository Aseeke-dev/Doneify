from pwdlib import PasswordHash
import secrets

passwordhash = PasswordHash.recommended()

def hash_password(password: str):
    return passwordhash.hash(password)

def verify_password(new_password, hashed_password):
    return passwordhash.verify(new_password, hashed_password)

def generate_4_digit_code():
    return f"{secrets.randbelow(1000):04d}"