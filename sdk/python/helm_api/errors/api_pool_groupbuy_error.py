from __future__ import annotations

from dataclasses import dataclass
from typing import Final, TypeAlias

from ..core import ErrorMapper, RawError, decode_json
from ..models.error_out import ErrorOut
from ..models.http_validation_error import HttpValidationError

ApiPoolGroupbuyErrorBody: TypeAlias = ErrorOut | HttpValidationError | RawError


@dataclass(frozen=True, slots=True)
class _ApiPoolGroupbuyError:
    def map(self, status_code: int, content: bytes) -> ApiPoolGroupbuyErrorBody:
        match status_code:
            case 400:
                return decode_json[ErrorOut](content)
            case 422:
                return decode_json[HttpValidationError](content)
            case _:
                return RawError(status_code, content)


api_pool_groupbuy_error_mapper: Final[ErrorMapper[ApiPoolGroupbuyErrorBody]] = _ApiPoolGroupbuyError()
