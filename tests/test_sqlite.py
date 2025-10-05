import pytest

from sqlbind_t import E, sqlite
from sqlbind_t.dialect import unwrap

dialect = sqlite.Dialect()
dialect.IN_MAX_VALUES = 3


def test_IN() -> None:
    val = E.val
    assert unwrap(val.IN([]), dialect=dialect) == ('0', [])
    assert unwrap(val.IN([1, 'boo']), dialect=dialect) == ('val IN (?, ?)', [1, 'boo'])
    assert unwrap(val.IN([1, 'boo', 'bar', 'foo']), dialect=dialect) == (
        "val IN (1,'boo','bar','foo')",
        [],
    )

    with pytest.raises(ValueError, match='Invalid type'):
        unwrap(val.IN([{}, 'boo', 'bar', 'foo']), dialect=dialect)
