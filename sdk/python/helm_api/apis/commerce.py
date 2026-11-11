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
from ..errors.api_escrow_demo_error import ApiEscrowDemoErrorBody, api_escrow_demo_error_mapper
from ..errors.api_shop_buy_error import ApiShopBuyErrorBody, api_shop_buy_error_mapper
from ..errors.api_shop_search_error import ApiShopSearchErrorBody, api_shop_search_error_mapper
from ..models.escrow_in import EscrowIn, EscrowInDict
from ..models.escrow_out import EscrowOut
from ..models.shop_buy_in import ShopBuyIn, ShopBuyInDict
from ..models.shop_buy_out import ShopBuyOut
from ..models.shop_search_in import ShopSearchIn, ShopSearchInDict
from ..models.shop_search_out import ShopSearchOut
from ..server.server import Server


class Commerce:
    def __init__(self, client: RawClient, server: Server) -> None:
        self._with_raw_response = CommerceWithRawResponse(client, server)

    def api_escrow_demo(
        self, body: EscrowIn | EscrowInDict, *, request_options: RequestOptionsOrDict | None = None
    ) -> EscrowOut:
        """Pay-on-proof escrow: PayPal authorizes and holds the money, deterministic criteria decide release (capture)
        or refund (void). A cheat flag sends a junk delivery to show the money is returned, not released.

        Args:
            body: The request body.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            Successful Response

        Raises:
            ApiError: Bad Request Validation Error ``error`` is ``ErrorOut | HttpValidationError | RawError``."""
        return unwrap(self._with_raw_response.api_escrow_demo(body, request_options=request_options))

    def api_shop_buy(
        self, body: ShopBuyIn | ShopBuyInDict, *, request_options: RequestOptionsOrDict | None = None
    ) -> ShopBuyOut:
        """Buy a found product: the person's owner-signed spend mandate authorizes the purchase (budget and per-item cap
        enforced by the signature, not a rule), and pay-on-proof escrow settles it on PayPal. The same account that
        earns can spend.

        Args:
            body: The request body.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            Successful Response

        Raises:
            ApiError: Bad Request Validation Error ``error`` is ``ErrorOut | HttpValidationError | RawError``."""
        return unwrap(self._with_raw_response.api_shop_buy(body, request_options=request_options))

    def api_shop_search(
        self, body: ShopSearchIn | ShopSearchInDict, *, request_options: RequestOptionsOrDict | None = None
    ) -> ShopSearchOut:
        """The buyer side: a person spends earnings on a real product. Finds products with Channel3 when a key is set,
        or a demo catalog otherwise, and flags which fit the stated budget.

        Args:
            body: The request body.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            Successful Response

        Raises:
            ApiError: Bad Request Validation Error ``error`` is ``ErrorOut | HttpValidationError | RawError``."""
        return unwrap(self._with_raw_response.api_shop_search(body, request_options=request_options))

    @property
    def with_raw_response(self) -> CommerceWithRawResponse:
        return self._with_raw_response


class AsyncCommerce:
    def __init__(self, client: AsyncRawClient, server: Server) -> None:
        self._with_raw_response = AsyncCommerceWithRawResponse(client, server)

    async def api_escrow_demo(
        self, body: EscrowIn | EscrowInDict, *, request_options: RequestOptionsOrDict | None = None
    ) -> EscrowOut:
        """Pay-on-proof escrow: PayPal authorizes and holds the money, deterministic criteria decide release (capture)
        or refund (void). A cheat flag sends a junk delivery to show the money is returned, not released.

        Args:
            body: The request body.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            Successful Response

        Raises:
            ApiError: Bad Request Validation Error ``error`` is ``ErrorOut | HttpValidationError | RawError``."""
        return unwrap(await self._with_raw_response.api_escrow_demo(body, request_options=request_options))

    async def api_shop_buy(
        self, body: ShopBuyIn | ShopBuyInDict, *, request_options: RequestOptionsOrDict | None = None
    ) -> ShopBuyOut:
        """Buy a found product: the person's owner-signed spend mandate authorizes the purchase (budget and per-item cap
        enforced by the signature, not a rule), and pay-on-proof escrow settles it on PayPal. The same account that
        earns can spend.

        Args:
            body: The request body.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            Successful Response

        Raises:
            ApiError: Bad Request Validation Error ``error`` is ``ErrorOut | HttpValidationError | RawError``."""
        return unwrap(await self._with_raw_response.api_shop_buy(body, request_options=request_options))

    async def api_shop_search(
        self, body: ShopSearchIn | ShopSearchInDict, *, request_options: RequestOptionsOrDict | None = None
    ) -> ShopSearchOut:
        """The buyer side: a person spends earnings on a real product. Finds products with Channel3 when a key is set,
        or a demo catalog otherwise, and flags which fit the stated budget.

        Args:
            body: The request body.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            Successful Response

        Raises:
            ApiError: Bad Request Validation Error ``error`` is ``ErrorOut | HttpValidationError | RawError``."""
        return unwrap(await self._with_raw_response.api_shop_search(body, request_options=request_options))

    @property
    def with_raw_response(self) -> AsyncCommerceWithRawResponse:
        return self._with_raw_response


class CommerceWithRawResponse(BaseRawResponse[RawClient, Server]):
    def api_escrow_demo(
        self, body: EscrowIn | EscrowInDict, *, request_options: RequestOptionsOrDict | None = None
    ) -> ApiResult[EscrowOut, ApiEscrowDemoErrorBody]:
        """Pay-on-proof escrow: PayPal authorizes and holds the money, deterministic criteria decide release (capture)
        or refund (void). A cheat flag sends a junk delivery to show the money is returned, not released.

        Args:
            body: The request body.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            An ``ApiResult`` holding the deserialized response or the error body."""
        return self._client.execute(
            http_method="POST",
            url_template=self._server.default("/api/escrow/demo"),
            headers=[param[UUID]("Idempotency-Key", uuid4())],
            body=json_body[EscrowIn | EscrowInDict](body),
            decoder=json_decoder[EscrowOut],
            error_mapper=api_escrow_demo_error_mapper,
            request_options=request_options,
        )

    def api_shop_buy(
        self, body: ShopBuyIn | ShopBuyInDict, *, request_options: RequestOptionsOrDict | None = None
    ) -> ApiResult[ShopBuyOut, ApiShopBuyErrorBody]:
        """Buy a found product: the person's owner-signed spend mandate authorizes the purchase (budget and per-item cap
        enforced by the signature, not a rule), and pay-on-proof escrow settles it on PayPal. The same account that
        earns can spend.

        Args:
            body: The request body.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            An ``ApiResult`` holding the deserialized response or the error body."""
        return self._client.execute(
            http_method="POST",
            url_template=self._server.default("/api/shop/buy"),
            headers=[param[UUID]("Idempotency-Key", uuid4())],
            body=json_body[ShopBuyIn | ShopBuyInDict](body),
            decoder=json_decoder[ShopBuyOut],
            error_mapper=api_shop_buy_error_mapper,
            request_options=request_options,
        )

    def api_shop_search(
        self, body: ShopSearchIn | ShopSearchInDict, *, request_options: RequestOptionsOrDict | None = None
    ) -> ApiResult[ShopSearchOut, ApiShopSearchErrorBody]:
        """The buyer side: a person spends earnings on a real product. Finds products with Channel3 when a key is set,
        or a demo catalog otherwise, and flags which fit the stated budget.

        Args:
            body: The request body.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            An ``ApiResult`` holding the deserialized response or the error body."""
        return self._client.execute(
            http_method="POST",
            url_template=self._server.default("/api/shop/search"),
            headers=[param[UUID]("Idempotency-Key", uuid4())],
            body=json_body[ShopSearchIn | ShopSearchInDict](body),
            decoder=json_decoder[ShopSearchOut],
            error_mapper=api_shop_search_error_mapper,
            request_options=request_options,
        )


class AsyncCommerceWithRawResponse(BaseRawResponse[AsyncRawClient, Server]):
    async def api_escrow_demo(
        self, body: EscrowIn | EscrowInDict, *, request_options: RequestOptionsOrDict | None = None
    ) -> ApiResult[EscrowOut, ApiEscrowDemoErrorBody]:
        """Pay-on-proof escrow: PayPal authorizes and holds the money, deterministic criteria decide release (capture)
        or refund (void). A cheat flag sends a junk delivery to show the money is returned, not released.

        Args:
            body: The request body.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            An ``ApiResult`` holding the deserialized response or the error body."""
        return await self._client.execute(
            http_method="POST",
            url_template=self._server.default("/api/escrow/demo"),
            headers=[param[UUID]("Idempotency-Key", uuid4())],
            body=json_body[EscrowIn | EscrowInDict](body),
            decoder=async_json_decoder[EscrowOut],
            error_mapper=api_escrow_demo_error_mapper,
            request_options=request_options,
        )

    async def api_shop_buy(
        self, body: ShopBuyIn | ShopBuyInDict, *, request_options: RequestOptionsOrDict | None = None
    ) -> ApiResult[ShopBuyOut, ApiShopBuyErrorBody]:
        """Buy a found product: the person's owner-signed spend mandate authorizes the purchase (budget and per-item cap
        enforced by the signature, not a rule), and pay-on-proof escrow settles it on PayPal. The same account that
        earns can spend.

        Args:
            body: The request body.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            An ``ApiResult`` holding the deserialized response or the error body."""
        return await self._client.execute(
            http_method="POST",
            url_template=self._server.default("/api/shop/buy"),
            headers=[param[UUID]("Idempotency-Key", uuid4())],
            body=json_body[ShopBuyIn | ShopBuyInDict](body),
            decoder=async_json_decoder[ShopBuyOut],
            error_mapper=api_shop_buy_error_mapper,
            request_options=request_options,
        )

    async def api_shop_search(
        self, body: ShopSearchIn | ShopSearchInDict, *, request_options: RequestOptionsOrDict | None = None
    ) -> ApiResult[ShopSearchOut, ApiShopSearchErrorBody]:
        """The buyer side: a person spends earnings on a real product. Finds products with Channel3 when a key is set,
        or a demo catalog otherwise, and flags which fit the stated budget.

        Args:
            body: The request body.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            An ``ApiResult`` holding the deserialized response or the error body."""
        return await self._client.execute(
            http_method="POST",
            url_template=self._server.default("/api/shop/search"),
            headers=[param[UUID]("Idempotency-Key", uuid4())],
            body=json_body[ShopSearchIn | ShopSearchInDict](body),
            decoder=async_json_decoder[ShopSearchOut],
            error_mapper=api_shop_search_error_mapper,
            request_options=request_options,
        )
