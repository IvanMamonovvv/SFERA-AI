import pytest
from fastapi import HTTPException

from sfera_ai.api.auth import make_bff_secret_dependency


def test_valid_secret_passes():
    require = make_bff_secret_dependency("expected")
    require(x_bff_shared_secret="expected")


def test_wrong_secret_raises_401():
    require = make_bff_secret_dependency("expected")
    with pytest.raises(HTTPException) as exc_info:
        require(x_bff_shared_secret="wrong")
    assert exc_info.value.status_code == 401


def test_missing_secret_raises_401():
    require = make_bff_secret_dependency("expected")
    with pytest.raises(HTTPException) as exc_info:
        require(x_bff_shared_secret=None)
    assert exc_info.value.status_code == 401
