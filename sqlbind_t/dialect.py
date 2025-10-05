from collections.abc import Collection
from typing import Generic, TypeVar, Union

from .query_params import QueryParams

T = TypeVar('T')


class DialectOp(Generic[T]):
    method: str

    def __init__(self, field: str, value: T):
        self.field = field
        self.value = value

    def to_sql(self, params: QueryParams, dialect: 'Dialect') -> str:
        return getattr(dialect, self.method)(self, params)  # type: ignore[no-any-return]


class IN_Op(DialectOp[Union[Collection[object]]]):
    method = 'IN'


class LIKE_Op(DialectOp[str]):
    method = 'LIKE'
    op: str
    template: str


class Dialect:
    FALSE = 'FALSE'
    LIKE_ESCAPE = '\\'
    LIKE_CHARS = '%_'

    def IN(self, op: IN_Op, params: QueryParams) -> str:
        if op.value:
            return f'{op.field} IN {params.compile(op.value)}'
        return self.FALSE

    def LIKE(self, op: LIKE_Op, params: QueryParams) -> str:
        value = like_escape(op.value, self.LIKE_ESCAPE, self.LIKE_CHARS)
        return f'{op.field} {op.op} {params.compile(op.template.format(value))}'


def like_escape(value: str, escape: str = '\\', likechars: str = '%_') -> str:
    r"""Escapes special LIKE characters

    In general application couldn't use untrusted input in LIKE
    expressions because it could easily lead to incorrect results in best case
    and DDoS in worst.

    >>> like_escape('my_tag')
    'my\\_tag'

    Note: LIKE and Expr.LIKE provides more convenient way to use it.
    """
    value = value.replace(escape, escape + escape)
    for c in likechars:
        value = value.replace(c, escape + c)
    return value
