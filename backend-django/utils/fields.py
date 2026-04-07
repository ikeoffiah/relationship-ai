from .encryption import encrypt, decrypt


def decrypt_field_value(user, encrypted_value):
    """Utility to decrypt a value given a user context (using HKDF)."""
    if not encrypted_value or not user:
        return encrypted_value

    if isinstance(encrypted_value, str) and encrypted_value.startswith("ENC:"):
        actual_value = encrypted_value[4:]
        user_id = str(user.id)
        return decrypt(actual_value, user_id)

    return encrypted_value


def encrypt_field_value(user, plaintext_value):
    """Utility to encrypt a value given a user context (using HKDF)."""
    if not plaintext_value or not user:
        return plaintext_value

    user_id = str(user.id)
    return "ENC:" + encrypt(str(plaintext_value), user_id)
