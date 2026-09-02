import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt import PyJWK
from jwt.algorithms import RSAAlgorithm

from backend.app.core.auth import InvalidAccessToken, SupabaseJwtVerifier


class StaticJwksClient:
    def __init__(self, key: PyJWK) -> None:
        self.key = key

    def get_signing_key_from_jwt(self, token: str) -> PyJWK:
        return self.key


def verifier_and_key() -> tuple[SupabaseJwtVerifier, rsa.RSAPrivateKey]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = json.loads(RSAAlgorithm.to_jwk(private_key.public_key()))
    jwk.update({"kid": "synthetic-test-key", "alg": "RS256", "use": "sig"})
    verifier = SupabaseJwtVerifier(
        "https://synthetic.supabase.co/auth/v1",
        "authenticated",
        StaticJwksClient(PyJWK.from_dict(jwk)),
    )
    return verifier, private_key


def make_token(
    private_key: rsa.RSAPrivateKey,
    *,
    role: str = "authenticated",
    audience: str = "authenticated",
) -> tuple[str, str]:
    user_id = str(uuid4())
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": user_id,
            "role": role,
            "aud": audience,
            "iss": "https://synthetic.supabase.co/auth/v1",
            "iat": now,
            "exp": now + timedelta(minutes=5),
        },
        private_key,
        algorithm="RS256",
        headers={"kid": "synthetic-test-key"},
    )
    return token, user_id


def test_verifier_accepts_authenticated_user_token() -> None:
    verifier, private_key = verifier_and_key()
    token, user_id = make_token(private_key)

    user = verifier.verify(token)

    assert str(user.id) == user_id
    assert user.role == "authenticated"


@pytest.mark.parametrize(
    ("role", "audience"),
    [("service_role", "authenticated"), ("authenticated", "wrong-audience")],
)
def test_verifier_rejects_privileged_or_wrong_audience_tokens(
    role: str, audience: str
) -> None:
    verifier, private_key = verifier_and_key()
    token, _ = make_token(private_key, role=role, audience=audience)

    with pytest.raises(InvalidAccessToken):
        verifier.verify(token)
