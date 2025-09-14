from typing import (
    Dict,
    Iterator,
    List,
    Optional,
    Sequence,
    Tuple,
    Union,
    overload,
)

from .query_params import ParamsT, QMarkQueryParams, QueryParams
from .template import Interpolation, Template

UNDEFINED = object()

Part = Union[str, Interpolation]
AnySQL = Union['SQL', Template]


class SQL(Template):
    def __init__(self, *parts: Part) -> None:
        self._parts = parts

    def __iter__(self) -> Iterator[Part]:
        return iter(self._parts)

    def __or__(self, other: AnySQL) -> 'SQL':
        return OR(self, other)

    def __and__(self, other: AnySQL) -> 'SQL':
        return AND(self, other)

    def __invert__(self) -> 'SQL':
        if self:
            return SQL('NOT ', Interpolation(self))
        else:
            return EMPTY

    def __bool__(self) -> bool:
        return bool(len(self._parts))

    @overload
    def split(self) -> Tuple[str, QMarkQueryParams]: ...

    @overload
    def split(self, params: ParamsT) -> Tuple[str, ParamsT]: ...

    def split(self, params: Optional[ParamsT] = None) -> Tuple[str, ParamsT]:
        lparams: ParamsT
        if params is None:
            lparams = QMarkQueryParams()  # type: ignore[assignment]
        else:
            lparams = params
        return ''.join(self._walk(self, lparams)), lparams

    def _walk(self, query: AnySQL, params: QueryParams) -> Iterator[str]:
        for it in query:
            if type(it) is str:
                yield it
            else:
                if isinstance(it.value, Template):  # type: ignore[union-attr]
                    yield from self._walk(it.value, params)  # type: ignore[union-attr]
                else:
                    yield params.compile(it.value)  # type: ignore[union-attr]


class Compound(SQL):
    def __init__(
        self,
        prefix: str,
        sep: str,
        tlist: Sequence[AnySQL],
        wrap: Optional[Tuple[str, str]] = None,
    ) -> None:
        self._prefix = prefix
        self._sep = sep
        self._wrap = wrap
        self._tlist = tlist

    def __iter__(self) -> Iterator[Part]:
        if self._prefix:
            yield self._prefix

        if self._wrap:
            yield self._wrap[0]

        sep = self._sep
        for i, it in enumerate(self._tlist):
            if i > 0:
                yield sep
            yield Interpolation(it)

        if self._wrap:
            yield self._wrap[1]

    def __bool__(self) -> bool:
        return True


EMPTY = SQL()


def text(expr: str) -> SQL:
    return SQL(expr)


def sql(template: AnySQL) -> SQL:
    if isinstance(template, SQL):
        return template

    for it in template:
        if isinstance(it, Interpolation) and it.value is UNDEFINED:
            return EMPTY

    return SQL(*template)


def AND(*fragments: AnySQL) -> SQL:
    return join_fragments(' AND ', fragments, ('(', ')'))


def OR(*fragments: AnySQL) -> SQL:
    return join_fragments(' OR ', fragments, ('(', ')'))


def join_fragments(
    sep: str, flist: Sequence[AnySQL], wrap: Optional[Tuple[str, str]] = None, prefix: str = ''
) -> SQL:
    flist = list(filter(None, flist))
    if not flist:
        return EMPTY
    elif len(flist) == 1:
        return Compound(prefix, sep, flist)

    return Compound(prefix, sep, flist, wrap)


def WHERE(*cond: AnySQL, **kwargs: object) -> SQL:
    flist = list(sql(it) for it in cond) + [
        SQL(f'{field} IS NULL') if value is None else SQL(f'{field} = ', Interpolation(value))
        for field, value in kwargs.items()
        if value is not UNDEFINED
    ]
    return join_fragments(' AND ', flist, prefix='WHERE ')


def VALUES(data: Optional[List[Dict[str, object]]] = None, **kwargs: object) -> SQL:
    if data is None:
        data = [kwargs]

    names = list(data[0].keys())
    result: List[Part] = [f'({", ".join(names)}) VALUES ']
    for it in data:
        result.append('(')
        for f in names:
            result.extend((Interpolation(it[f]), ', '))
        result.pop()
        result.append(')')
        result.append(', ')

    result.pop()
    return SQL(*result)


def assign(**kwargs: object) -> SQL:
    flist = [
        SQL(f'{field} = ', Interpolation(value))
        for field, value in kwargs.items()
        if value is not UNDEFINED
    ]
    return join_fragments(', ', flist)


def SET(**kwargs: object) -> SQL:
    return SQL('SET ', *assign(**kwargs))


class NotNone:
    def __truediv__(self, other: object) -> object:
        if other is None:
            return UNDEFINED
        return other


not_none = NotNone()


def _in_range(field: str, lop: str, left: object, rop: str, right: object) -> SQL:
    return AND(
        SQL(f'{field} {lop} ', Interpolation(left)) if left is not None else EMPTY,
        SQL(f'{field} {rop} ', Interpolation(right)) if right is not None else EMPTY,
    )


def in_range(field: str, left: object, right: object) -> SQL:
    return _in_range(field, '>=', left, '<', right)


def in_crange(field: str, left: object, right: object) -> SQL:
    return _in_range(field, '>=', left, '<=', right)
