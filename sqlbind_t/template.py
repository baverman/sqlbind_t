import ast
import sys
from ast import Expression, FormattedValue
from typing import Iterator, List, Union


class Interpolation:
    def __init__(self, value: object) -> None:
        self.value = value

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f'Interpolation({self.value!r})'


TemplatePart = Union[str, Interpolation]


class Template:
    def __init__(self, *parts: TemplatePart):
        self._parts = parts

    def __iter__(self) -> Iterator[TemplatePart]:
        return iter(self._parts)

    def __bool__(self) -> bool:
        return bool(self._parts)


def parse_template(string: str) -> Template:
    root = ast.parse('f' + repr(string), mode='eval')
    frame = sys._getframe(1)
    values: List[Union[str, Interpolation]] = []
    for it in root.body.values:  # type: ignore[attr-defined]
        if type(it) is FormattedValue:
            code = compile(Expression(it.value), '<string>', 'eval')
            value = eval(code, frame.f_globals, frame.f_locals)
            values.append(Interpolation(value))
        else:
            values.append(it.value)
    return Template(*values)


t = parse_template
