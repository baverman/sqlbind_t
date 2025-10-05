from textwrap import dedent

import pytest

from sqlbind_t import (
    EMPTY,
    IN,
    SET,
    UNDEFINED,
    VALUES,
    WHERE,
    E,
    cond,
    in_crange,
    in_range,
    not_none,
    sql,
    sqlf,
    sqls,
    text,
    truthy,
)
from sqlbind_t.dialect import like_escape, unwrap
from sqlbind_t.template import HAS_TSTRINGS, Interpolation
from sqlbind_t.tfstring import check_template as t


def test_simple() -> None:
    s, p = unwrap(sqls('SELECT * from {text("boo")} WHERE name = {10}'))
    assert s == 'SELECT * from boo WHERE name = ?'
    assert p == [10]


def test_simple_tf_strings() -> None:
    s, p = unwrap(sqlf(f'@SELECT * from {text("boo")} WHERE name = {10}'))
    assert s == 'SELECT * from boo WHERE name = ?'
    assert p == [10]


@pytest.mark.skipif(not HAS_TSTRINGS, reason='no t-strings')
def test_tstrings() -> None:
    code = """\
        name = 'boo'
        table = t'foo'
        cond = sql(t'name = {name}')
        result = unwrap(t'SELECT * FROM {table} WHERE {cond}')
        assert result == ('SELECT * FROM foo WHERE name = ?', ['boo']), result
    """
    exec(dedent(code))


def test_where_kwargs() -> None:
    q = WHERE(some=not_none / 10, null=None, empty=not_none / None)
    assert unwrap(q) == ('WHERE some = ? AND null IS NULL', [10])

    assert unwrap(sql(WHERE(EMPTY))) == ('', [])


def test_where_args() -> None:
    q = WHERE(sqlf(f'@f1 = {not_none / None}'), sqlf(f'@f2 = {10}'))
    assert q
    assert unwrap(q) == ('WHERE f2 = ?', [10])


@pytest.mark.skipif(HAS_TSTRINGS, reason='std template could have unstable repr')
def test_repr() -> None:
    q = WHERE(sqlf(f'@f1 = {not_none / None}'), sqlf(f'@f2 = {10}'))
    assert repr(q) == "Compound('WHERE ', Interpolation(SQL('f2 = ', Interpolation(10))))"

    assert repr(Interpolation(10)) == 'Interpolation(10)'
    assert str(Interpolation(10)) == '10'


def test_in_range() -> None:
    col = E.col
    assert unwrap(in_range(col, 10, 20)) == ('(col >= ? AND col < ?)', [10, 20])
    assert unwrap(in_range(col, 10, None)) == ('col >= ?', [10])
    assert unwrap(in_range(col, None, 20)) == ('col < ?', [20])
    assert unwrap(in_range(col, None, None)) == ('', [])
    assert unwrap(in_crange(col, 10, 20)) == ('(col >= ? AND col <= ?)', [10, 20])

    assert unwrap(in_range(text('field + 20'), 10, 20)) == (
        '(field + 20 >= ? AND field + 20 < ?)',
        [10, 20],
    )


def test_values() -> None:
    q = f'@INSERT INTO boo {VALUES(boo=10, foo=None)}'
    assert unwrap(sqlf(q)) == ('INSERT INTO boo (boo, foo) VALUES (?, ?)', [10, None])


def test_set() -> None:
    q = f'@UPDATE boo {SET(boo=10, foo=None, bar=not_none / None)}'
    assert unwrap(sqlf(q)) == ('UPDATE boo SET boo = ?, foo = ?', [10, None])


def test_sql_ops() -> None:
    q = text('some') & t(f'@{10}')
    assert unwrap(q) == ('(some AND ?)', [10])

    q = text('some') | t(f'@{10}')
    assert unwrap(q) == ('(some OR ?)', [10])

    q = ~sql(t(f'@{10}'))
    assert unwrap(q) == ('NOT ?', [10])

    assert unwrap(~EMPTY) == ('', [])


def test_expr() -> None:
    val = E.val
    assert unwrap(val < 1) == ('val < ?', [1])
    assert unwrap(val <= 1) == ('val <= ?', [1])
    assert unwrap(val > 1) == ('val > ?', [1])
    assert unwrap(val >= 1) == ('val >= ?', [1])
    assert unwrap(val == 1) == ('val = ?', [1])
    assert unwrap(val == None) == ('val IS NULL', [])  # noqa: E711
    assert unwrap(val != truthy / 1) == ('val != ?', [1])
    assert unwrap(val != None) == ('val IS NOT NULL', [])  # noqa: E711
    assert unwrap(~val) == ('NOT val', [])

    assert (val == not_none / None) is EMPTY
    assert (val == truthy / 0) is EMPTY

    assert unwrap(E('field + 10') < 1) == ('field + 10 < ?', [1])
    assert unwrap(val('"ugly name"') == 1) == ('val."ugly name" = ?', [1])

    assert unwrap(sqlf(f'@SELECT * FROM {E.table}')) == ('SELECT * FROM table', [])


def test_in() -> None:
    val = E.val
    assert unwrap(val.IN([10, 20])) == ('val IN ?', [[10, 20]])
    assert unwrap(val.IN([])) == ('FALSE', [])
    assert unwrap(val.IN(not_none / None)) == ('', [])

    assert unwrap(IN(sqlf(f'@field + {42}'), [10, 20])) == ('field + ? IN ?', [42, [10, 20]])


def test_like_escape() -> None:
    assert like_escape('boo') == 'boo'
    assert like_escape('boo%') == 'boo\\%'
    assert like_escape('boo_') == 'boo\\_'
    assert like_escape('boo\\') == 'boo\\\\'
    assert like_escape('%b\\oo_|', '|') == '|%b\\oo|_||'


def test_like() -> None:
    tag = E.tag
    assert unwrap(tag.LIKE('{}%', 'my_tag')) == ('tag LIKE ?', ['my\\_tag%'])
    assert unwrap(tag.ILIKE('{}%', 'my_tag')) == ('tag ILIKE ?', ['my\\_tag%'])
    assert unwrap(tag.LIKE('{}%', not_none / None)) == ('', [])


def test_cond() -> None:
    is_true = cond(True)
    is_false = cond(False)
    assert is_true / 10 == 10
    assert is_false / 10 is UNDEFINED
