from collections.abc import Collection
from typing import Generic, Iterator, Optional, Tuple, TypeVar, Union, overload

from . import SQL, AnySQL, Expr, SafeStr
from .query_params import ParamsT, QMarkQueryParams, QueryParams
from .template import Template

T = TypeVar('T')


class DialectOp(Generic[T]):
    method: str

    def __init__(self, field: SafeStr, value: T):
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
            f = self.unwrap_safe(op.field, params)
            return f'{f} IN {params.compile(op.value)}'
        return self.FALSE

    def LIKE(self, op: LIKE_Op, params: QueryParams) -> str:
        f = self.unwrap_safe(op.field, params)
        value = like_escape(op.value, self.LIKE_ESCAPE, self.LIKE_CHARS)
        return f'{f} {op.op} {params.compile(op.template.format(value))}'

    def unwrap_safe(self, value: SafeStr, params: QueryParams) -> str:
        if isinstance(value, Expr):
            return value._left
        return unwrap(value, params=params, dialect=self)[0]  # type: ignore[call-overload,no-any-return]


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


@overload
def unwrap(query: AnySQL) -> Tuple[str, QMarkQueryParams]: ...


@overload
def unwrap(query: AnySQL, *, dialect: Dialect) -> Tuple[str, QMarkQueryParams]: ...


@overload
def unwrap(query: AnySQL, params: ParamsT) -> Tuple[str, ParamsT]: ...


def unwrap(
    query: AnySQL, params: Optional[ParamsT] = None, dialect: Dialect = Dialect()
) -> Tuple[str, ParamsT]:
    lparams: ParamsT
    if params is None:
        lparams = QMarkQueryParams()  # type: ignore[assignment]
    else:
        lparams = params
    return ''.join(_walk(query, lparams, dialect)), lparams


def _walk(query: AnySQL, params: QueryParams, dialect: Dialect) -> Iterator[str]:
    for it in query:
        if type(it) is str:
            yield it
        else:
            if isinstance(it.value, (Template, SQL)):  # type: ignore[union-attr]
                yield from _walk(it.value, params, dialect)  # type: ignore[union-attr]
            elif isinstance(it.value, DialectOp):  # type: ignore[union-attr]
                yield it.value.to_sql(params, dialect)  # type: ignore[union-attr]
            else:
                yield params.compile(it.value)  # type: ignore[union-attr]
