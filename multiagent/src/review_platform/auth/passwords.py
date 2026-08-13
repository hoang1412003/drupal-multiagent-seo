"""Password policy va Argon2id hashing cho tai khoan Platform Admin."""
from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerificationError


MIN_PASSWORD_LENGTH = 12
MAX_PASSWORD_LENGTH = 128

HASHER = PasswordHasher(
    time_cost=2,
    memory_cost=19456,
    parallelism=1,
    hash_len=32,
    salt_len=16,
    type=Type.ID,
)


class PasswordPolicyError(ValueError):
    pass


def validate_password(password: str) -> None:
    """Validate do dai tren chuoi goc; tuyet doi khong trim/normalize password."""
    if not isinstance(password, str):
        raise PasswordPolicyError("password phải là chuỗi")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise PasswordPolicyError(
            f"password phải có ít nhất {MIN_PASSWORD_LENGTH} ký tự"
        )
    if len(password) > MAX_PASSWORD_LENGTH:
        raise PasswordPolicyError(
            f"password không được quá {MAX_PASSWORD_LENGTH} ký tự"
        )


def hash_password(password: str) -> str:
    validate_password(password)
    return HASHER.hash(password)


def verify_password(hash_value: str, password: str) -> bool:
    """Khong de caller phan biet mismatch va hash bi hong/sai dinh dang."""
    try:
        return HASHER.verify(hash_value, password)
    except (VerificationError, InvalidHashError, TypeError):
        return False


def needs_rehash(hash_value: str) -> bool:
    try:
        return HASHER.check_needs_rehash(hash_value)
    except (InvalidHashError, TypeError):
        return True
