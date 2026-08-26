import pytest
from sqlalchemy import create_engine


@pytest.fixture()
def tmp_engine():
    return create_engine("sqlite:///:memory:")
