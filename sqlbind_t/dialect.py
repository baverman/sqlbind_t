from typing import Generic, Iterator, Optional, Tuple, TypeVar, Union, overload

from . import SQL, AnySQL, Expr, SafeStr
from .compat import Collection
from .query_params import ParamsT, QMarkQueryParams, QueryParams
from .template import Interpolation, Template

T = TypeVar('T')


class DialectOp(Generic[T]):
    method: str

    def __init__(self, field: SafeStr, value: T):
        self.field = field
        self.value = value

    def render(self, params: QueryParams, dialect: 'Dialect') -> str:
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
            f = self.safe_str(op.field, params)
            return f'{f} IN {params.compile(op.value)}'
        return self.FALSE

    def LIKE(self, op: LIKE_Op, params: QueryParams) -> str:
        f = self.safe_str(op.field, params)
        value = like_escape(op.value, self.LIKE_ESCAPE, self.LIKE_CHARS)
        return f'{f} {op.op} {params.compile(op.template.format(value))}'

    def safe_str(self, value: SafeStr, params: QueryParams) -> str:
        if isinstance(value, Expr):
            return value._left
        return ''.join(self._walk(value, params))

    @overload
    def render(self, query: AnySQL) -> Tuple[str, QMarkQueryParams]: ...

    @overload
    def render(self, query: AnySQL, params: ParamsT) -> Tuple[str, ParamsT]: ...

    def render(self, query: AnySQL, params: Optional[ParamsT] = None) -> Tuple[str, ParamsT]:
        lparams: ParamsT
        if params is None:
            lparams = QMarkQueryParams()  # type: ignore[assignment]
        else:
            lparams = params
        return ''.join(self._walk(query, lparams)), lparams

    def _walk(self, query: AnySQL, params: QueryParams) -> Iterator[str]:
        for it in query:
            if type(it) is str:
                yield it
            else:
                value: Interpolation = it.value  # type: ignore[union-attr,assignment]
                if isinstance(value, (Template, SQL)):
                    yield from self._walk(value, params)
                elif isinstance(value, DialectOp):
                    yield value.render(params, self)
                elif isinstance(value, Expr):
                    yield value._left
                else:
                    yield params.compile(value)


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


render = Dialect().render
