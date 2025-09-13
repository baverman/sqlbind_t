from typing import Dict, List, TypeVar

ParamsT = TypeVar('ParamsT', bound='QueryParams')


class QueryParams:
    def compile(self, value: object) -> str:  # pragma: no cover
        raise NotImplementedError


class ListQueryParams(QueryParams, List[object]):
    pass


class DictQueryParams(QueryParams, Dict[str, object]):
    def __init__(self) -> None:
        dict.__init__(self, {})
        self._count = 0

    def add(self, value: object) -> str:
        name = f'p{self._count}'
        self[name] = value
        self._count += 1
        return name


class QMarkQueryParams(ListQueryParams):
    """QueryParams implementation for qmark (?) parameter style"""

    def compile(self, value: object) -> str:
        self.append(value)
        return '?'


class FormatQueryParams(ListQueryParams):
    """QueryParams implementation for format (%s) parameter style"""

    def compile(self, value: object) -> str:
        self.append(value)
        return '%s'


class NumericQueryParams(ListQueryParams):
    """QueryParams implementation for numeric (:1, :2) parameter style"""

    def compile(self, value: object) -> str:
        self.append(value)
        return f':{len(self)}'


class DollarQueryParams(ListQueryParams):
    """QueryParams implementation for format ($1, $2, ...) parameter style"""

    def compile(self, value: object) -> str:
        self.append(value)
        return f'${len(self)}'


class NamedQueryParams(DictQueryParams):
    """QueryParams implementation for named (:name) parameter style"""

    def compile(self, value: object) -> str:
        return f':{self.add(value)}'


class PyFormatQueryParams(DictQueryParams):
    """QueryParams implementation for pyformat (%(name)s) parameter style"""

    def compile(self, value: object) -> str:
        return f'%({self.add(value)})s'
