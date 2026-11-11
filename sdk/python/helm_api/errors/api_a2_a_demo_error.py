from __future__ import annotations

from dataclasses import dataclass
from typing import Final, TypeAlias

from ..core import ErrorMapper, RawError, decode_json
from ..models.error_out import ErrorOut

ApiA2ADemoErrorBody: TypeAlias = ErrorOut | RawError


@dataclass(frozen=True, slots=True)
class _ApiA2ADemoError:
    def map(self, status_code: int, content: bytes) -> ApiA2ADemoErrorBody:
        match status_code:
            case 400:
                return decode_json[ErrorOut](content)
            case _:
                return RawError(status_code, content)


api_a2_a_demo_error_mapper: Final[ErrorMapper[ApiA2ADemoErrorBody]] = _ApiA2ADemoError()
