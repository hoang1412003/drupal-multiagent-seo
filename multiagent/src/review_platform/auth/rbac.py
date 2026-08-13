"""Role va thu tu quyen dung chung cho Platform Admin."""
from enum import Enum


class Role(str, Enum):
    VIEWER = "viewer"
    OPERATOR = "operator"
    ADMIN = "admin"


ROLE_RANK = {
    Role.VIEWER: 10,
    Role.OPERATOR: 20,
    Role.ADMIN: 30,
}


def allows(actual: Role, required: Role) -> bool:
    return ROLE_RANK[Role(actual)] >= ROLE_RANK[Role(required)]
