import sys
from typing import TYPE_CHECKING

__all__ = ['Collection']
pyver = sys.version_info[:2]

if TYPE_CHECKING:
    from collections.abc import Collection
else:
    if pyver < (3, 9):
        from typing import Collection  # pragma: no cover
    else:
        from collections.abc import Collection
