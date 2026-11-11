from __future__ import annotations

from typing import Any

from ..core import (
    ApiResult,
    AsyncRawClient,
    BaseRawResponse,
    RawClient,
    RawError,
    RequestOptionsOrDict,
    async_empty_response,
    async_json_decoder,
    async_text_decoder,
    empty_response,
    json_decoder,
    raw_error_response,
    text_decoder,
    unwrap,
)
from ..server.server import Server


class Dashboard:
    def __init__(self, client: RawClient, server: Server) -> None:
        self._with_raw_response = DashboardWithRawResponse(client, server)

    def data(self, *, request_options: RequestOptionsOrDict | None = None) -> Any:
        """The complete cached dashboard payload (headline, scenarios, directory, reinvest, engine).

        Args:
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            Successful Response

        Raises:
            ApiError: If the API responds with an error status code. ``error`` is ``RawError``."""
        return unwrap(self._with_raw_response.data(request_options=request_options))

    def healthz(self, *, request_options: RequestOptionsOrDict | None = None) -> str:
        """Returns 'ok' when the server is up.

        Args:
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            Successful Response

        Raises:
            ApiError: If the API responds with an error status code. ``error`` is ``RawError``."""
        return unwrap(self._with_raw_response.healthz(request_options=request_options))

    def index(self, *, request_options: RequestOptionsOrDict | None = None) -> None:
        """Serve the single-page dashboard with its data embedded.

        Args:
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            Successful Response

        Raises:
            ApiError: If the API responds with an error status code. ``error`` is ``RawError``."""
        return unwrap(self._with_raw_response.index(request_options=request_options))

    @property
    def with_raw_response(self) -> DashboardWithRawResponse:
        return self._with_raw_response


class AsyncDashboard:
    def __init__(self, client: AsyncRawClient, server: Server) -> None:
        self._with_raw_response = AsyncDashboardWithRawResponse(client, server)

    async def data(self, *, request_options: RequestOptionsOrDict | None = None) -> Any:
        """The complete cached dashboard payload (headline, scenarios, directory, reinvest, engine).

        Args:
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            Successful Response

        Raises:
            ApiError: If the API responds with an error status code. ``error`` is ``RawError``."""
        return unwrap(await self._with_raw_response.data(request_options=request_options))

    async def healthz(self, *, request_options: RequestOptionsOrDict | None = None) -> str:
        """Returns 'ok' when the server is up.

        Args:
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            Successful Response

        Raises:
            ApiError: If the API responds with an error status code. ``error`` is ``RawError``."""
        return unwrap(await self._with_raw_response.healthz(request_options=request_options))

    async def index(self, *, request_options: RequestOptionsOrDict | None = None) -> None:
        """Serve the single-page dashboard with its data embedded.

        Args:
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            Successful Response

        Raises:
            ApiError: If the API responds with an error status code. ``error`` is ``RawError``."""
        return unwrap(await self._with_raw_response.index(request_options=request_options))

    @property
    def with_raw_response(self) -> AsyncDashboardWithRawResponse:
        return self._with_raw_response


class DashboardWithRawResponse(BaseRawResponse[RawClient, Server]):
    def data(self, *, request_options: RequestOptionsOrDict | None = None) -> ApiResult[Any, RawError]:
        """The complete cached dashboard payload (headline, scenarios, directory, reinvest, engine).

        Args:
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            An ``ApiResult`` holding the deserialized response or the error body."""
        return self._client.execute(
            http_method="GET",
            url_template=self._server.default("/api/data"),
            decoder=json_decoder[Any],
            error_mapper=raw_error_response,
            request_options=request_options,
        )

    def healthz(self, *, request_options: RequestOptionsOrDict | None = None) -> ApiResult[str, RawError]:
        """Returns 'ok' when the server is up.

        Args:
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            An ``ApiResult`` holding the deserialized response or the error body."""
        return self._client.execute(
            http_method="GET",
            url_template=self._server.default("/healthz"),
            decoder=text_decoder[str],
            error_mapper=raw_error_response,
            request_options=request_options,
        )

    def index(self, *, request_options: RequestOptionsOrDict | None = None) -> ApiResult[None, RawError]:
        """Serve the single-page dashboard with its data embedded.

        Args:
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            An ``ApiResult`` holding the deserialized response or the error body."""
        return self._client.execute(
            http_method="GET",
            url_template=self._server.default("/"),
            decoder=empty_response,
            error_mapper=raw_error_response,
            request_options=request_options,
        )


class AsyncDashboardWithRawResponse(BaseRawResponse[AsyncRawClient, Server]):
    async def data(self, *, request_options: RequestOptionsOrDict | None = None) -> ApiResult[Any, RawError]:
        """The complete cached dashboard payload (headline, scenarios, directory, reinvest, engine).

        Args:
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            An ``ApiResult`` holding the deserialized response or the error body."""
        return await self._client.execute(
            http_method="GET",
            url_template=self._server.default("/api/data"),
            decoder=async_json_decoder[Any],
            error_mapper=raw_error_response,
            request_options=request_options,
        )

    async def healthz(self, *, request_options: RequestOptionsOrDict | None = None) -> ApiResult[str, RawError]:
        """Returns 'ok' when the server is up.

        Args:
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            An ``ApiResult`` holding the deserialized response or the error body."""
        return await self._client.execute(
            http_method="GET",
            url_template=self._server.default("/healthz"),
            decoder=async_text_decoder[str],
            error_mapper=raw_error_response,
            request_options=request_options,
        )

    async def index(self, *, request_options: RequestOptionsOrDict | None = None) -> ApiResult[None, RawError]:
        """Serve the single-page dashboard with its data embedded.

        Args:
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            An ``ApiResult`` holding the deserialized response or the error body."""
        return await self._client.execute(
            http_method="GET",
            url_template=self._server.default("/"),
            decoder=async_empty_response,
            error_mapper=raw_error_response,
            request_options=request_options,
        )
