from collections.abc import Collection
from typing import Union

from sqlbind_t.dialect import Dialect as BaseDialect
from sqlbind_t.dialect import IN_Op
from sqlbind_t.query_params import QueryParams


class Dialect(BaseDialect):
    FALSE = '0'
    IN_MAX_VALUES = 10

    def IN(self, op: IN_Op, params: QueryParams) -> str:
        values: Collection[Union[float, int, str]] = op.value  # type: ignore[assignment]
        if not values:
            return self.FALSE

        if len(values) > self.IN_MAX_VALUES:
            # Trying to escape and assemble SQL manually to avoid too many
            # parameters exception
            return f'{op.field} IN ({sqlite_value_list(values)})'

        mark_list = ', '.join(params.compile(it) for it in values)
        return f'{op.field} IN ({mark_list})'


def sqlite_escape(val: Union[float, int, str]) -> str:
    tval = type(val)
    if tval is str:
        return "'{}'".format(val.replace("'", "''"))  # type: ignore[union-attr]
    elif tval is int or tval is float:
        return str(val)
    raise ValueError(f'Invalid type: {val}')


def sqlite_value_list(values: Collection[Union[float, int, str]]) -> str:
    return ','.join(map(sqlite_escape, values))
