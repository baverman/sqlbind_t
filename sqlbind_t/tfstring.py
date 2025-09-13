import importlib.abc
import sys
from ast import (
    AST,
    Call,
    Constant,
    FormattedValue,
    ImportFrom,
    JoinedStr,
    Load,
    Module,
    Name,
    NodeTransformer,
    alias,
    copy_location,
    fix_missing_locations,
    parse,
)
from importlib.machinery import PathFinder
from typing import List

from .template import Template

PREFIX = '!! '
IMPORTED_CALL_NAME = '__sqlbind_t_template'
IMPORTED_INTERPOLATE_NAME = '__sqlbind_t_interpolate'


class FStringTransformer(NodeTransformer):
    def visit_JoinedStr(self, node: JoinedStr) -> AST:
        if type(node.values[0]) is Constant and node.values[0].value.startswith(PREFIX):  # type: ignore[union-attr,arg-type]
            self.has_transform = True
            node.values[0].value = node.values[0].value[len(PREFIX) :]  # type: ignore[index]
            replace = []
            for value in node.values:
                arg: AST
                if type(value) is FormattedValue:
                    arg = copy_location(
                        Call(
                            func=Name(id=IMPORTED_INTERPOLATE_NAME, ctx=Load()),
                            args=[value.value],
                            keywords=[],
                        ),
                        value,
                    )
                else:
                    arg = value
                replace.append(arg)
            return copy_location(
                Call(func=Name(id=IMPORTED_CALL_NAME, ctx=Load()), args=replace, keywords=[]),
                node,
            )
        return node


def transform_fstrings(tree: Module) -> Module:
    transformer = FStringTransformer()
    new_tree: Module = transformer.visit(tree)

    if getattr(transformer, 'has_transform', None):
        new_tree.body.insert(
            0,
            ImportFrom(
                module='sqlbind_t.template',
                names=[
                    alias(name='Template', asname=IMPORTED_CALL_NAME),
                    alias(name='Interpolation', asname=IMPORTED_INTERPOLATE_NAME),
                ],
                level=0,
            ),
        )

    fix_missing_locations(new_tree)
    return new_tree


def check_template(arg: str) -> Template:
    # arg is str from type checker perspective, but transform
    # converts prefixed f-strings into a Template instances.
    if isinstance(arg, Template):
        return arg
    raise RuntimeError(
        f't (check_template) accepts only a prefixed f-string like t(f"{PREFIX} ...")'
    )


t = check_template


class TransformingLoader(importlib.abc.SourceLoader):
    def __init__(self, fullname: str, path: str) -> None:
        self.fullname = fullname
        self.path = path

    def get_filename(self, fullname: str) -> str:
        return self.path

    def get_data(self, path: str) -> bytes:
        with open(path, 'rb') as f:
            return f.read()

    def source_to_code(self, data, path, *, _optimize=-1):  # type: ignore[no-untyped-def,override]
        tree = parse(data, filename=path)
        new_tree = transform_fstrings(tree)
        return compile(new_tree, path, 'exec', optimize=_optimize)


class TransformingFinder(PathFinder):
    def __init__(self, prefixes: List[str]) -> None:
        self._sqlbind_prefixes = prefixes

    def find_spec(self, fullname, path, target=None):  # type: ignore[no-untyped-def,override]
        spec = super().find_spec(fullname, path, target=target)
        if any(fullname.startswith(it) for it in self._sqlbind_prefixes):
            if spec and spec.origin and spec.origin.endswith('.py'):
                spec.loader = TransformingLoader(fullname, spec.origin)
                return spec
        return spec


def init(prefixes: List[str]) -> None:
    sys.meta_path.insert(0, TransformingFinder(prefixes))
