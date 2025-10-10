import sqlbind_t.query_params as qp
from sqlbind_t import sqlf
from sqlbind_t.dialect import render


def test_query_params() -> None:
    q = sqlf(f'@SELECT {10}, {20}')

    assert render(q, qp.QMarkQueryParams()) == ('SELECT ?, ?', [10, 20])
    assert render(q, qp.NumericQueryParams()) == ('SELECT :1, :2', [10, 20])
    assert render(q, qp.DollarQueryParams()) == ('SELECT $1, $2', [10, 20])
    assert render(q, qp.FormatQueryParams()) == ('SELECT %s, %s', [10, 20])

    assert render(q, qp.NamedQueryParams()) == ('SELECT :p0, :p1', {'p0': 10, 'p1': 20})
    assert render(q, qp.PyFormatQueryParams()) == ('SELECT %(p0)s, %(p1)s', {'p0': 10, 'p1': 20})
