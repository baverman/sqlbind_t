from collections.abc import Collection
from typing import (
    Dict,
    Iterator,
    List,
    Optional,
    Sequence,
    Tuple,
    TypeVar,
    Union,
)

from .template import Interpolation, NTemplate, Template, parse_template
from .tfstring import check_template

version = '0.1'


class UndefinedType:
    pass


Part = Union[str, Interpolation]
AnySQL = Union['SQL', Template]
T = TypeVar('T')
UNDEFINED = UndefinedType()
SafeStr = Union['Expr', 'SQL', Template]


class SQL(NTemplate):
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


def sqls(template: str) -> SQL:
    return sql(parse_template(template, level=2))


def sqlf(template: Union[AnySQL, str]) -> SQL:
    return sql(check_template(template))  # type: ignore[arg-type]


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
    def __truediv__(self, other: Optional[T]) -> Union[T, UndefinedType]:
        if other is None:
            return UNDEFINED
        return other


class Truthy:
    def __truediv__(self, other: Optional[T]) -> Union[T, UndefinedType]:
        if not other:
            return UNDEFINED
        return other


class Condition:
    def __init__(self, cond: object) -> None:
        self._cond = bool(cond)

    def __truediv__(self, other: T) -> Union[T, UndefinedType]:
        if not self._cond:
            return UNDEFINED
        return other


not_none = NotNone()
truthy = Truthy()
cond = Condition


def unwrap_safe(value: SafeStr) -> Union[str, Interpolation]:
    if isinstance(value, Expr):
        return value._left
    return Interpolation(value)


def _in_range(field: SafeStr, lop: str, left: object, rop: str, right: object) -> SQL:
    f = unwrap_safe(field)
    return AND(
        SQL(f, f' {lop} ', Interpolation(left)) if left is not None else EMPTY,
        SQL(f, f' {rop} ', Interpolation(right)) if right is not None else EMPTY,
    )


def in_range(field: SafeStr, left: object, right: object) -> SQL:
    return _in_range(field, '>=', left, '<', right)


def in_crange(field: SafeStr, left: object, right: object) -> SQL:
    return _in_range(field, '>=', left, '<=', right)


def op2(left: str, right: object) -> SQL:
    if right is UNDEFINED:
        return EMPTY
    return SQL(left, Interpolation(right))


def IN(field: SafeStr, value: Union[Collection[object], UndefinedType]) -> SQL:
    if value is UNDEFINED:
        return EMPTY
    return SQL(Interpolation(IN_Op(field, list(value))))  # type: ignore[arg-type]


def LIKE(field: SafeStr, template: str, value: Union[str, UndefinedType], op: str = 'LIKE') -> SQL:
    r"""Renders LIKE expression with escaped value.

    template is a LIKE pattern with `{}` as a value placeholder, for example:

    * `{}%`: startswith
    * `%{}`: endswith
    * `%{}%`: contains

    >>> q.LIKE('tag', '{}%', 'my_tag')
    'tag LIKE ?'
    >>> q
    ['my\\_tag%']
    >>> q.LIKE('tag', '{}%', not_none/None)  # supports UNDEFINED values
    ''
    """
    if value is UNDEFINED:
        return EMPTY

    dop = LIKE_Op(field, value)  # type: ignore[arg-type]
    dop.op = op
    dop.template = template
    return SQL(Interpolation(dop))


def ILIKE(field: SafeStr, template: str, value: Union[str, UndefinedType]) -> SQL:
    return LIKE(field, template, value, 'ILIKE')


class Expr:
    def __init__(self, left: str = ''):
        self._left = left

    def __getattr__(self, name: str) -> 'Expr':
        if self._left:
            return Expr(f'{self._left}.{name}')
        return self.__class__(name)

    def __call__(self, name: str) -> 'Expr':
        if self._left:
            return self.__class__(f'{self._left}.{name}')
        return self.__class__(name)

    def __lt__(self, right: object) -> SQL:
        return op2(f'{self._left} < ', right)

    def __le__(self, right: object) -> SQL:
        return op2(f'{self._left} <= ', right)

    def __gt__(self, right: object) -> SQL:
        return op2(f'{self._left} > ', right)

    def __ge__(self, right: object) -> SQL:
        return op2(f'{self._left} >= ', right)

    def __eq__(self, right: object) -> SQL:  # type: ignore[override]
        if right is None:
            return SQL(f'{self._left} IS NULL')
        return op2(f'{self._left} = ', right)

    def __ne__(self, right: object) -> SQL:  # type: ignore[override]
        if right is None:
            return SQL(f'{self._left} IS NOT NULL')
        return op2(f'{self._left} != ', right)

    def __invert__(self) -> SQL:
        return SQL('NOT ' + self._left)

    def IN(self, right: Union[Collection[object], UndefinedType]) -> SQL:
        return IN(self, right)

    def LIKE(self, template: str, right: Union[str, UndefinedType]) -> SQL:
        return LIKE(self, template, right)

    def ILIKE(self, template: str, right: Union[str, UndefinedType]) -> SQL:
        return ILIKE(self, template, right)


E = Expr()

from .dialect import IN_Op, LIKE_Op
