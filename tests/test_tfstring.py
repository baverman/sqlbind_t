import ast
from textwrap import dedent

import pytest

from sqlbind_t.tfstring import transform_fstrings


def execute(source):
    new = transform_fstrings(ast.parse(source))
    code = compile(new, '<string>', 'exec')
    ctx = {}
    exec(code, ctx, ctx)
    return ctx


def test_simple():
    ctx = execute(
        dedent(
            """\
                from sqlbind_t.tfstring import t
                def boo(name):
                    return t(f'!! SELECT {name}')
            """
        )
    )

    p1, p2 = list(ctx['boo']('zoom'))
    assert p1 == 'SELECT '
    assert p2.value == 'zoom'


def test_type_check():
    ctx = execute(
        dedent(
            """\
                from sqlbind_t.tfstring import t
                def boo(name):
                    return t(f'SELECT {name}')
            """
        )
    )
    with pytest.raises(RuntimeError, match='prefixed f-string'):
        ctx['boo']('zoom')
