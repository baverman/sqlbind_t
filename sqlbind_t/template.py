import ast
import sys
from ast import Expression, FormattedValue
from typing import TYPE_CHECKING, Iterator, List, Union

HAS_TSTRINGS = sys.version_info[:2] >= (3, 14)

TemplatePart = Union[str, 'Interpolation']

__all__ = ['Template', 'Interpolation']


class NTemplate:
    def __init__(self, *parts: TemplatePart):
        self._parts = parts

    def __iter__(self) -> Iterator[TemplatePart]:
        return iter(self._parts)

    def __bool__(self) -> bool:
        return bool(self._parts)

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({", ".join(map(repr, self))})'


class NInterpolation:
    def __init__(self, value: object) -> None:
        self.value = value

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f'Interpolation({self.value!r})'


if TYPE_CHECKING:
    Template = NTemplate
    Interpolation = NInterpolation
else:
    if HAS_TSTRINGS:  # pragma: no cover
        from string.templatelib import Interpolation, Template
    else:
        Template = NTemplate
        Interpolation = NInterpolation


def parse_template(string: str, *, level: int = 1) -> Template:
    root = ast.parse('f' + repr(string), mode='eval')
    frame = sys._getframe(level)
    values: List[Union[str, Interpolation]] = []
    for it in root.body.values:  # type: ignore[attr-defined]
        if type(it) is FormattedValue:
            code = compile(Expression(it.value), '<string>', 'eval')
            value = eval(code, frame.f_globals, frame.f_locals)
            values.append(Interpolation(value))
        else:
            values.append(it.value)
    return Template(*values)
