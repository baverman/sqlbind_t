import pytest

from sqlbind_t import E, sqlite

dialect = sqlite.Dialect()
dialect.IN_MAX_VALUES = 3


def test_IN() -> None:
    val = E.val
    assert val.IN([]).split(dialect=dialect) == ('0', [])
    assert val.IN([1, 'boo']).split(dialect=dialect) == ('val IN (?, ?)', [1, 'boo'])
    assert val.IN([1, 'boo', 'bar', 'foo']).split(dialect=dialect) == (
        "val IN (1,'boo','bar','foo')",
        [],
    )

    with pytest.raises(ValueError, match='Invalid type'):
        val.IN([{}, 'boo', 'bar', 'foo']).split(dialect=dialect)
