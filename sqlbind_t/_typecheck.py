from typing_extensions import assert_type

from . import SQL, WHERE
from .dialect import Dialect, unwrap
from .query_params import NumericQueryParams, QMarkQueryParams


def test_return_type_for_default_split() -> None:
    result = unwrap(SQL())
    assert_type(result[1], QMarkQueryParams)

    result = unwrap(SQL(), dialect=Dialect())
    assert_type(result[1], QMarkQueryParams)


def test_return_type_for_split() -> None:
    result = unwrap(SQL(), NumericQueryParams())
    assert_type(result[1], NumericQueryParams)

    result = unwrap(SQL(), NumericQueryParams(), Dialect())
    assert_type(result[1], NumericQueryParams)

    result = unwrap(SQL(), NumericQueryParams(), dialect=Dialect())
    assert_type(result[1], NumericQueryParams)


def test_where_should_error_on_str() -> None:
    _ = WHERE('str')  # type: ignore[arg-type]
