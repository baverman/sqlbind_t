from typing_extensions import assert_type

from . import SQL
from .query_params import NumericQueryParams, QMarkQueryParams


def test_return_type_for_default_split() -> None:
    result = SQL().split()
    assert_type(result[1], QMarkQueryParams)


def test_return_type_for_split() -> None:
    result = SQL().split(NumericQueryParams())
    assert_type(result[1], NumericQueryParams)
