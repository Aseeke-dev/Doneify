import asyncio
from types import SimpleNamespace
from typing import cast

import pytest
from fastapi import HTTPException

from app.core.security import generate_4_digit_code, hash_password
from app.repositories.auth import AuthRepository
from app.services.auth import AuthService


def test_generate_4_digit_code_has_exactly_four_digits() -> None:
    code = generate_4_digit_code()

    assert len(code) == 4
    assert code.isdecimal()


def test_authenticate_user_accepts_verified_user() -> None:
    user = SimpleNamespace(
        email="verified@example.com",
        password=hash_password("correct-password"),
        is_verified=True,
    )
    service = AuthService.__new__(AuthService)
    fake_repository: AuthRepository = cast(
        AuthRepository,
        SimpleNamespace(get_user_by_email=lambda email: asyncio.sleep(0, result=user)),
    )
    service.authrepo = fake_repository

    result = asyncio.run(
        service.authenticate_user("verified@example.com", "correct-password")
    )

    assert result is user


@pytest.mark.parametrize(
    ("password", "verified", "expected_detail"),
    [
        ("wrong-password", True, "Invalid credentials"),
        ("correct-password", False, "Email not verified. Kindly verify your email"),
    ],
)
def test_authenticate_user_rejects_invalid_or_unverified_user(
    password: str,
    verified: bool,
    expected_detail: str,
) -> None:
    user = SimpleNamespace(
        email="user@example.com",
        password=hash_password("correct-password"),
        is_verified=verified,
    )
    service = AuthService.__new__(AuthService)
    fake_repository: AuthRepository = cast(
        AuthRepository,
        SimpleNamespace(get_user_by_email=lambda email: asyncio.sleep(0, result=user)),
    )
    service.authrepo = fake_repository

    with pytest.raises(HTTPException) as error:
        asyncio.run(service.authenticate_user("user@example.com", password))

    assert error.value.status_code == (
        401 if expected_detail == "Invalid credentials" else 403
    )
    assert error.value.detail == expected_detail