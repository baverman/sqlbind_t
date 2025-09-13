from typing import Any

from sqlbind_t import (
    EMPTY,
    SET,
    SQL,
    VALUES,
    WHERE,
    QMarkQueryParams,
    in_range,
    not_none,
    text,
)
from sqlbind_t.template import Interpolation
from sqlbind_t.template import t as tt
from sqlbind_t.tfstring import t


def render(sql: SQL) -> tuple[str, list[Any]]:
    return QMarkQueryParams().render(sql)


def test_repr():
    assert repr(Interpolation(10)) == 'Interpolation(10)'
    assert str(Interpolation(10)) == '10'


def test_simple():
    s, p = render(tt('SELECT * from {text("boo")} WHERE name = {10}'))
    assert s == 'SELECT * from boo WHERE name = ?'
    assert p == [10]


def test_simple_tf_strings():
    s, p = render(t(f'!! SELECT * from {text("boo")} WHERE name = {10}'))
    assert s == 'SELECT * from boo WHERE name = ?'
    assert p == [10]


def test_where():
    sql = WHERE(some=not_none / 10, null=None, empty=not_none / None)
    assert render(sql) == ('WHERE some = ? AND null IS NULL', [10])

    assert render(WHERE(EMPTY)) == ('', [])


def test_in_range():
    assert render(in_range('col', 10, 20)) == ('(col >= ? AND col < ?)', [10, 20])
    assert render(in_range('col', 10, None)) == ('col >= ?', [10])
    assert render(in_range('col', None, 20)) == ('col < ?', [20])
    assert render(in_range('col', None, None)) == ('', [])


def test_values():
    sql = t(f'!! INSERT INTO boo {VALUES(boo=10, foo=None)}')
    assert render(sql) == ('INSERT INTO boo (boo, foo) VALUES (?, ?)', [10, None])


def test_set():
    sql = t(f'!! UPDATE boo {SET(boo=10, foo=None, bar=not_none / None)}')
    assert render(sql) == ('UPDATE boo SET boo = ?, foo = ?', [10, None])


def test_sql_ops():
    sql = text('some') & t(f'!! {10}')
    assert render(sql) == ('(some AND ?)', [10])

    sql = text('some') | t(f'!! {10}')
    assert render(sql) == ('(some OR ?)', [10])

    sql = ~SQL(t(f'!! {10}'))
    assert render(sql) == ('NOT ?', [10])
