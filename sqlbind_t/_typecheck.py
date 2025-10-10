from typing_extensions import assert_type

from . import SQL, WHERE, Expr
from .dialect import render
from .query_params import NumericQueryParams, QMarkQueryParams


def test_return_type_for_default_split() -> None:
    result = render(SQL())
    assert_type(result[1], QMarkQueryParams)


def test_return_type_for_split() -> None:
    result = render(SQL(), NumericQueryParams())
    assert_type(result[1], NumericQueryParams)


def test_where_should_error_on_str() -> None:
    _ = WHERE('str')  # type: ignore[arg-type]


def test_expr_extension_should_keep_original_type() -> None:
    class MyExpr(Expr):
        pass

    val = MyExpr().val
    assert_type(val, MyExpr)
