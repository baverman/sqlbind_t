from typing import Dict, Iterator, List, Optional, Sequence, Tuple, Union

from .template import Interpolation, Template

UNDEFINED = object()


Part = Union[str, Interpolation]
SQLType = Union['SQLTemplate', Template]


class SQLTemplate(Template):
    def __init__(self, *parts: Part) -> None:
        self._parts = parts

    def __iter__(self) -> Iterator[Part]:
        return iter(self._parts)

    def __or__(self, other: SQLType) -> 'SQLTemplate':
        return OR(self, other)

    def __and__(self, other: SQLType) -> 'SQLTemplate':
        return AND(self, other)

    def __invert__(self) -> 'SQLTemplate':
        if self:
            return SQLTemplate('NOT ', Interpolation(self))
        else:
            return EMPTY

    def __bool__(self) -> bool:
        return bool(len(self._parts))


class SQL(SQLTemplate):
    def __init__(self, template: Template) -> None:
        super().__init__(Interpolation(template))


class Compound(SQLTemplate):
    def __init__(
        self,
        prefix: str,
        sep: str,
        tlist: Sequence[SQLType],
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


EMPTY = SQLTemplate()


def AND(*fragments: SQLType) -> SQLTemplate:
    return join_fragments(' AND ', fragments, ('(', ')'))


def OR(*fragments: SQLType) -> SQLTemplate:
    return join_fragments(' OR ', fragments, ('(', ')'))


def join_fragments(
    sep: str, flist: Sequence[SQLType], wrap: Optional[Tuple[str, str]] = None, prefix: str = ''
) -> SQLTemplate:
    flist = list(filter(None, flist))
    if not flist:
        return EMPTY
    elif len(flist) == 1:
        return Compound(prefix, sep, flist)

    return Compound(prefix, sep, flist, wrap)


def WHERE(*cond: SQLType, **kwargs: object) -> SQLTemplate:
    flist = list(cond) + [
        SQLTemplate(f'{field} IS NULL')
        if value is None
        else SQLTemplate(f'{field} = ', Interpolation(value))
        for field, value in kwargs.items()
        if value is not UNDEFINED
    ]
    return join_fragments(' AND ', flist, prefix='WHERE ')


def VALUES(data: Optional[List[Dict[str, object]]] = None, **kwargs: object) -> SQLTemplate:
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
    return SQLTemplate(*result)


def assign(**kwargs: object) -> SQLTemplate:
    flist = [
        SQLTemplate(f'{field} = ', Interpolation(value))
        for field, value in kwargs.items()
        if value is not UNDEFINED
    ]
    return join_fragments(', ', flist)


def SET(**kwargs: object) -> SQLTemplate:
    return SQLTemplate('SET ', *assign(**kwargs))


def text(expr: str) -> SQLTemplate:
    return SQLTemplate(expr)


class NotNone:
    def __truediv__(self, other: object) -> object:
        if other is None:
            return UNDEFINED
        return other


not_none = NotNone()


def _in_range(field: str, lop: str, left: object, rop: str, right: object) -> SQLTemplate:
    return AND(
        SQLTemplate(f'{field} {lop} ', Interpolation(left)) if left is not None else EMPTY,
        SQLTemplate(f'{field} {rop} ', Interpolation(right)) if right is not None else EMPTY,
    )


def in_range(field: str, left: object, right: object) -> SQLTemplate:
    return _in_range(field, '>=', left, '<', right)


def in_crange(field: str, left: object, right: object) -> SQLTemplate:
    return _in_range(field, '>=', left, '<=', right)


class ListQueryParams:
    mark: str

    def render(self, sql: SQLType) -> Tuple[str, List[object]]:
        params: List[object] = []
        return ''.join(self.iter(sql, params)), params

    def iter(self, sql: SQLType, params: List[object]) -> Iterator[str]:
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
