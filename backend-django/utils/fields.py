from .encryption import encrypt, decrypt


def decrypt_field_value(user, encrypted_value):
    """Utility to decrypt a value given a user context (using HKDF)."""
    if not encrypted_value or not user:
        return encrypted_value

    user_id = str(user.id)
    return decrypt(encrypted_value, user_id)


def encrypt_field_value(user, plaintext_value):
    """Utility to encrypt a value given a user context (using HKDF)."""
    if not plaintext_value or not user:
        return plaintext_value

    user_id = str(user.id)
    return encrypt(str(plaintext_value), user_id)
