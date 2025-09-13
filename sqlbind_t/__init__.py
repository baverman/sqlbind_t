from typing import Any, Dict, Iterator, List, Optional, Sequence, Tuple, Union

from .template import Interpolation, Template

UNDEFINED = object()


Part = Union[str, Interpolation]
SQLType = Union['SQL', Template]


class SQL(Template):
    def __init__(self, template: SQLType) -> None:
        self._template = template

    def __iter__(self) -> Iterator[Part]:
        yield Interpolation(self._template)

    def __or__(self, other: SQLType) -> 'SQL':
        return OR(self, other)

    def __and__(self, other: SQLType) -> 'SQL':
        return AND(self, other)

    def __invert__(self) -> 'SQL':
        if self:
            return SQLText('NOT ', Interpolation(self))
        else:
            return EMPTY

    def __bool__(self) -> bool:
        return True


class SQLText(SQL):
    def __init__(self, *parts: Part) -> None:
        self._parts = parts

    def __iter__(self) -> Iterator[Part]:
        return iter(self._parts)


class Compound(SQL):
    def __init__(
        self,
        prefix: str,
        sep: str,
        flist: Sequence[SQLType],
        wrap: Optional[Tuple[str, str]] = None,
    ) -> None:
        self._prefix = prefix
        self._sep = sep
        self._wrap = wrap
        self._flist = flist

    def __iter__(self) -> Iterator[Part]:
        if self._prefix:
            yield self._prefix

        if self._wrap:
            yield self._wrap[0]

        sep = self._sep
        for i, it in enumerate(self._flist):
            if i > 0:
                yield sep
            yield Interpolation(it)

        if self._wrap:
            yield self._wrap[1]


class EmptyType(SQL):
    def __init__(self) -> None:
        pass

    def __iter__(self) -> Iterator[Part]:
        return iter([])

    def __bool__(self) -> bool:
        return False


EMPTY = EmptyType()


def AND(*fragments: SQLType) -> SQL:
    return join_fragments(' AND ', fragments, ('(', ')'))


def OR(*fragments: SQLType) -> SQL:
    return join_fragments(' OR ', fragments, ('(', ')'))


def join_fragments(
    sep: str, flist: Sequence[SQLType], wrap: Optional[Tuple[str, str]] = None, prefix: str = ''
) -> SQL:
    flist = list(filter(None, flist))
    if not flist:
        return EMPTY
    elif len(flist) == 1:
        return Compound(prefix, sep, flist)

    return Compound(prefix, sep, flist, wrap)


def WHERE(*cond: SQL, **kwargs: Any) -> SQL:
    flist = list(cond) + [
        SQLText(f'{field} IS NULL')
        if value is None
        else SQLText(f'{field} = ', Interpolation(value))
        for field, value in kwargs.items()
        if value is not UNDEFINED
    ]
    return join_fragments(' AND ', flist, prefix='WHERE ')


def VALUES(data: Optional[List[Dict[str, Any]]] = None, **kwargs: Any) -> SQL:
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
    return SQLText(*result)


def assign(**kwargs: Any) -> SQL:
    flist = [
        SQLText(f'{field} = ', Interpolation(value))
        for field, value in kwargs.items()
        if value is not UNDEFINED
    ]
    return join_fragments(', ', flist)


def SET(**kwargs: Any) -> SQL:
    return SQLText('SET ', *assign(**kwargs))


def text(expr: str) -> SQL:
    return SQLText(expr)


class NotNone:
    def __truediv__(self, other: Any) -> Any:
        if other is None:
            return UNDEFINED
        return other


not_none = NotNone()


def _in_range(field: str, lop: str, left: Any, rop: str, right: Any) -> SQL:
    return AND(
        SQLText(f'{field} {lop} ', Interpolation(left)) if left is not None else EMPTY,
        SQLText(f'{field} {rop} ', Interpolation(right)) if right is not None else EMPTY,
    )


def in_range(field: str, left: Any, right: Any) -> SQL:
    return _in_range(field, '>=', left, '<', right)


def in_crange(field: str, left: Any, right: Any) -> SQL:
    return _in_range(field, '>=', left, '<=', right)


class ListQueryParams:
    mark: str

    def render(self, sql: SQLType) -> Tuple[str, List[Any]]:
        params: List[Any] = []
        return ''.join(self.iter(sql, params)), params

    def iter(self, sql: SQLType, params: List[Any]) -> Iterator[str]:
        mark = self.mark
        for it in sql:
            if type(it) is str:
                yield it
            else:
                if isinstance(it.value, Template):  # type: ignore[union-attr]
                    yield from self.iter(it.value, params)  # type: ignore[union-attr]
                else:
                    yield mark
                    params.append(it.value)  # type: ignore[union-attr]


class QMarkQueryParams(ListQueryParams):
    mark = '?'
