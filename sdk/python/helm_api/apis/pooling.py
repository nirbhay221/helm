from __future__ import annotations

from uuid import UUID, uuid4

from ..core import (
    ApiResult,
    AsyncRawClient,
    BaseRawResponse,
    RawClient,
    RequestOptionsOrDict,
    async_json_decoder,
    json_body,
    json_decoder,
    param,
    unwrap,
)
from ..errors.api_pool_groupbuy_error import ApiPoolGroupbuyErrorBody, api_pool_groupbuy_error_mapper
from ..errors.api_pool_invest_error import ApiPoolInvestErrorBody, api_pool_invest_error_mapper
from ..models.group_buy_in import GroupBuyIn, GroupBuyInDict
from ..models.group_buy_out import GroupBuyOut
from ..models.pool_invest_in import PoolInvestIn, PoolInvestInDict
from ..models.pool_invest_out import PoolInvestOut
from ..server.server import Server


class Pooling:
    def __init__(self, client: RawClient, server: Server) -> None:
        self._with_raw_response = PoolingWithRawResponse(client, server)

    def api_pool_groupbuy(
        self, body: GroupBuyIn | GroupBuyInDict, *, request_options: RequestOptionsOrDict | None = None
    ) -> GroupBuyOut:
        """Several people buy the same item together to clear a volume-discount tier none could reach alone. Each
        contribution is signed; the discounted total is shared pro-rata and the saving is attributed by the Shapley
        value.

        Args:
            body: The request body.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            Successful Response

        Raises:
            ApiError: Bad Request Validation Error ``error`` is ``ErrorOut | HttpValidationError | RawError``."""
        return unwrap(self._with_raw_response.api_pool_groupbuy(body, request_options=request_options))

    def api_pool_invest(
        self, body: PoolInvestIn | PoolInvestInDict, *, request_options: RequestOptionsOrDict | None = None
    ) -> PoolInvestOut:
        """Several people pool cash to co-own one position. The server signs each member's contribution with their own
        ES256 mandate, optionally forging one to show it is excluded, then places ONE real paper order for the pooled
        total and splits the units pro-rata.

        Args:
            body: The request body.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            Successful Response

        Raises:
            ApiError: Bad Request Validation Error ``error`` is ``ErrorOut | HttpValidationError | RawError``."""
        return unwrap(self._with_raw_response.api_pool_invest(body, request_options=request_options))

    @property
    def with_raw_response(self) -> PoolingWithRawResponse:
        return self._with_raw_response


class AsyncPooling:
    def __init__(self, client: AsyncRawClient, server: Server) -> None:
        self._with_raw_response = AsyncPoolingWithRawResponse(client, server)

    async def api_pool_groupbuy(
        self, body: GroupBuyIn | GroupBuyInDict, *, request_options: RequestOptionsOrDict | None = None
    ) -> GroupBuyOut:
        """Several people buy the same item together to clear a volume-discount tier none could reach alone. Each
        contribution is signed; the discounted total is shared pro-rata and the saving is attributed by the Shapley
        value.

        Args:
            body: The request body.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            Successful Response

        Raises:
            ApiError: Bad Request Validation Error ``error`` is ``ErrorOut | HttpValidationError | RawError``."""
        return unwrap(await self._with_raw_response.api_pool_groupbuy(body, request_options=request_options))

    async def api_pool_invest(
        self, body: PoolInvestIn | PoolInvestInDict, *, request_options: RequestOptionsOrDict | None = None
    ) -> PoolInvestOut:
        """Several people pool cash to co-own one position. The server signs each member's contribution with their own
        ES256 mandate, optionally forging one to show it is excluded, then places ONE real paper order for the pooled
        total and splits the units pro-rata.

        Args:
            body: The request body.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            Successful Response

        Raises:
            ApiError: Bad Request Validation Error ``error`` is ``ErrorOut | HttpValidationError | RawError``."""
        return unwrap(await self._with_raw_response.api_pool_invest(body, request_options=request_options))

    @property
    def with_raw_response(self) -> AsyncPoolingWithRawResponse:
        return self._with_raw_response


class PoolingWithRawResponse(BaseRawResponse[RawClient, Server]):
    def api_pool_groupbuy(
        self, body: GroupBuyIn | GroupBuyInDict, *, request_options: RequestOptionsOrDict | None = None
    ) -> ApiResult[GroupBuyOut, ApiPoolGroupbuyErrorBody]:
        """Several people buy the same item together to clear a volume-discount tier none could reach alone. Each
        contribution is signed; the discounted total is shared pro-rata and the saving is attributed by the Shapley
        value.

        Args:
            body: The request body.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            An ``ApiResult`` holding the deserialized response or the error body."""
        return self._client.execute(
            http_method="POST",
            url_template=self._server.default("/api/pool/groupbuy"),
            headers=[param[UUID]("Idempotency-Key", uuid4())],
            body=json_body[GroupBuyIn | GroupBuyInDict](body),
            decoder=json_decoder[GroupBuyOut],
            error_mapper=api_pool_groupbuy_error_mapper,
            request_options=request_options,
        )

    def api_pool_invest(
        self, body: PoolInvestIn | PoolInvestInDict, *, request_options: RequestOptionsOrDict | None = None
    ) -> ApiResult[PoolInvestOut, ApiPoolInvestErrorBody]:
        """Several people pool cash to co-own one position. The server signs each member's contribution with their own
        ES256 mandate, optionally forging one to show it is excluded, then places ONE real paper order for the pooled
        total and splits the units pro-rata.

        Args:
            body: The request body.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            An ``ApiResult`` holding the deserialized response or the error body."""
        return self._client.execute(
            http_method="POST",
            url_template=self._server.default("/api/pool/invest"),
            headers=[param[UUID]("Idempotency-Key", uuid4())],
            body=json_body[PoolInvestIn | PoolInvestInDict](body),
            decoder=json_decoder[PoolInvestOut],
            error_mapper=api_pool_invest_error_mapper,
            request_options=request_options,
        )


class AsyncPoolingWithRawResponse(BaseRawResponse[AsyncRawClient, Server]):
    async def api_pool_groupbuy(
        self, body: GroupBuyIn | GroupBuyInDict, *, request_options: RequestOptionsOrDict | None = None
    ) -> ApiResult[GroupBuyOut, ApiPoolGroupbuyErrorBody]:
        """Several people buy the same item together to clear a volume-discount tier none could reach alone. Each
        contribution is signed; the discounted total is shared pro-rata and the saving is attributed by the Shapley
        value.

        Args:
            body: The request body.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            An ``ApiResult`` holding the deserialized response or the error body."""
        return await self._client.execute(
            http_method="POST",
            url_template=self._server.default("/api/pool/groupbuy"),
            headers=[param[UUID]("Idempotency-Key", uuid4())],
            body=json_body[GroupBuyIn | GroupBuyInDict](body),
            decoder=async_json_decoder[GroupBuyOut],
            error_mapper=api_pool_groupbuy_error_mapper,
            request_options=request_options,
        )

    async def api_pool_invest(
        self, body: PoolInvestIn | PoolInvestInDict, *, request_options: RequestOptionsOrDict | None = None
    ) -> ApiResult[PoolInvestOut, ApiPoolInvestErrorBody]:
        """Several people pool cash to co-own one position. The server signs each member's contribution with their own
        ES256 mandate, optionally forging one to show it is excluded, then places ONE real paper order for the pooled
        total and splits the units pro-rata.

        Args:
            body: The request body.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            An ``ApiResult`` holding the deserialized response or the error body."""
        return await self._client.execute(
            http_method="POST",
            url_template=self._server.default("/api/pool/invest"),
            headers=[param[UUID]("Idempotency-Key", uuid4())],
            body=json_body[PoolInvestIn | PoolInvestInDict](body),
            decoder=async_json_decoder[PoolInvestOut],
            error_mapper=api_pool_invest_error_mapper,
            request_options=request_options,
        )
