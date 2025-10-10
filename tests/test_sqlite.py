import pytest

from sqlbind_t import E, sqlite

dialect = sqlite.Dialect()
dialect.IN_MAX_VALUES = 3


def test_IN() -> None:
    val = E.val
    assert dialect.render(val.IN([])) == ('0', [])
    assert dialect.render(val.IN([1, 'boo'])) == ('val IN (?, ?)', [1, 'boo'])
    assert dialect.render(val.IN([1, 'boo', 'bar', 'foo'])) == (
        "val IN (1,'boo','bar','foo')",
        [],
    )

    with pytest.raises(ValueError, match='Invalid type'):
        dialect.render(val.IN([{}, 'boo', 'bar', 'foo']))
