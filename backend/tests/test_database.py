import pytest

from backend.app.core.database import get_database_engine
from backend.app.core.settings import Settings


def test_ordinary_database_dependency_rejects_bypass_role() -> None:
    settings = Settings(
        database_url="postgresql+psycopg://synthetic.invalid/test",
        database_request_role="postgres",
    )

    with pytest.raises(
        RuntimeError, match="Ordinary requests must use the authenticated DB role"
    ):
        get_database_engine(settings)
