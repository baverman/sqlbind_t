from sqlbind_t import (
    EMPTY,
    SET,
    VALUES,
    WHERE,
    in_crange,
    in_range,
    not_none,
    sql,
    text,
)
from sqlbind_t.template import Interpolation
from sqlbind_t.template import t as tt
from sqlbind_t.tfstring import t, sql as sqlf


def test_repr():
    assert repr(Interpolation(10)) == 'Interpolation(10)'
    assert str(Interpolation(10)) == '10'


def test_simple():
    s, p = sql(tt('SELECT * from {text("boo")} WHERE name = {10}')).split()
    assert s == 'SELECT * from boo WHERE name = ?'
    assert p == [10]


def test_simple_tf_strings():
    s, p = sqlf(f'!! SELECT * from {text("boo")} WHERE name = {10}').split()
    assert s == 'SELECT * from boo WHERE name = ?'
    assert p == [10]


def test_where_kwargs():
    q = WHERE(some=not_none / 10, null=None, empty=not_none / None)
    assert q.split() == ('WHERE some = ? AND null IS NULL', [10])

    assert sql(WHERE(EMPTY)).split() == ('', [])


def test_where_args():
    q = WHERE(f'!! f1 = {not_none/None}', f'!! f2 = {10}')
    assert q
    assert repr(q) == "Compound('WHERE ', Interpolation(SQL('f2 = ', Interpolation(10))))"

    assert q.split() == ('WHERE f2 = ?', [10])


def test_in_range():
    assert in_range('col', 10, 20).split() == ('(col >= ? AND col < ?)', [10, 20])
    assert in_range('col', 10, None).split() == ('col >= ?', [10])
    assert in_range('col', None, 20).split() == ('col < ?', [20])
    assert in_range('col', None, None).split() == ('', [])
    assert in_crange('col', 10, 20).split() == ('(col >= ? AND col <= ?)', [10, 20])


def test_values():
    q = f'!! INSERT INTO boo {VALUES(boo=10, foo=None)}'
    assert sqlf(q).split() == ('INSERT INTO boo (boo, foo) VALUES (?, ?)', [10, None])


def test_set():
    q = f'!! UPDATE boo {SET(boo=10, foo=None, bar=not_none / None)}'
    assert sqlf(q).split() == ('UPDATE boo SET boo = ?, foo = ?', [10, None])


def test_sql_ops():
    q = text('some') & t(f'!! {10}')
    assert q.split() == ('(some AND ?)', [10])

    q = text('some') | t(f'!! {10}')
    assert q.split() == ('(some OR ?)', [10])

    q = ~sql(t(f'!! {10}'))
    assert q.split() == ('NOT ?', [10])

    assert (~EMPTY).split() == ('', [])
