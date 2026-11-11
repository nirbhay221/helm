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
from ..errors.api_a2_a_check_error import ApiA2ACheckErrorBody, api_a2_a_check_error_mapper
from ..errors.api_a2_a_demo_error import ApiA2ADemoErrorBody, api_a2_a_demo_error_mapper
from ..models.a2_a_check_in import A2ACheckIn, A2ACheckInDict
from ..models.a2_a_check_out import A2ACheckOut
from ..models.a2_a_demo_out import A2ADemoOut
from ..server.server import Server


class Agent:
    def __init__(self, client: RawClient, server: Server) -> None:
        self._with_raw_response = AgentWithRawResponse(client, server)

    def api_a2a_check(
        self, body: A2ACheckIn | A2ACheckInDict, *, request_options: RequestOptionsOrDict | None = None
    ) -> A2ACheckOut:
        """Verify a signed owner mandate and decide if a proposed deal is allowed.

        Args:
            body: The request body.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            Successful Response

        Raises:
            ApiError: Bad Request Validation Error ``error`` is ``ErrorOut | HttpValidationError | RawError``."""
        return unwrap(self._with_raw_response.api_a2a_check(body, request_options=request_options))

    def api_a2a_demo(self, *, request_options: RequestOptionsOrDict | None = None) -> A2ADemoOut:
        """Issue a fresh owner-signed intent mandate, plus a tampered copy of it, so the page can show live that a valid
        mandate verifies and a forged one is rejected. The key is generated per call and never leaves the server.

        Args:
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            Successful Response

        Raises:
            ApiError: Bad Request ``error`` is ``ErrorOut | RawError``."""
        return unwrap(self._with_raw_response.api_a2a_demo(request_options=request_options))

    @property
    def with_raw_response(self) -> AgentWithRawResponse:
        return self._with_raw_response


class AsyncAgent:
    def __init__(self, client: AsyncRawClient, server: Server) -> None:
        self._with_raw_response = AsyncAgentWithRawResponse(client, server)

    async def api_a2a_check(
        self, body: A2ACheckIn | A2ACheckInDict, *, request_options: RequestOptionsOrDict | None = None
    ) -> A2ACheckOut:
        """Verify a signed owner mandate and decide if a proposed deal is allowed.

        Args:
            body: The request body.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            Successful Response

        Raises:
            ApiError: Bad Request Validation Error ``error`` is ``ErrorOut | HttpValidationError | RawError``."""
        return unwrap(await self._with_raw_response.api_a2a_check(body, request_options=request_options))

    async def api_a2a_demo(self, *, request_options: RequestOptionsOrDict | None = None) -> A2ADemoOut:
        """Issue a fresh owner-signed intent mandate, plus a tampered copy of it, so the page can show live that a valid
        mandate verifies and a forged one is rejected. The key is generated per call and never leaves the server.

        Args:
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            Successful Response

        Raises:
            ApiError: Bad Request ``error`` is ``ErrorOut | RawError``."""
        return unwrap(await self._with_raw_response.api_a2a_demo(request_options=request_options))

    @property
    def with_raw_response(self) -> AsyncAgentWithRawResponse:
        return self._with_raw_response


class AgentWithRawResponse(BaseRawResponse[RawClient, Server]):
    def api_a2a_check(
        self, body: A2ACheckIn | A2ACheckInDict, *, request_options: RequestOptionsOrDict | None = None
    ) -> ApiResult[A2ACheckOut, ApiA2ACheckErrorBody]:
        """Verify a signed owner mandate and decide if a proposed deal is allowed.

        Args:
            body: The request body.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            An ``ApiResult`` holding the deserialized response or the error body."""
        return self._client.execute(
            http_method="POST",
            url_template=self._server.default("/api/a2a/check"),
            headers=[param[UUID]("Idempotency-Key", uuid4())],
            body=json_body[A2ACheckIn | A2ACheckInDict](body),
            decoder=json_decoder[A2ACheckOut],
            error_mapper=api_a2_a_check_error_mapper,
            request_options=request_options,
        )

    def api_a2a_demo(
        self, *, request_options: RequestOptionsOrDict | None = None
    ) -> ApiResult[A2ADemoOut, ApiA2ADemoErrorBody]:
        """Issue a fresh owner-signed intent mandate, plus a tampered copy of it, so the page can show live that a valid
        mandate verifies and a forged one is rejected. The key is generated per call and never leaves the server.

        Args:
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            An ``ApiResult`` holding the deserialized response or the error body."""
        return self._client.execute(
            http_method="GET",
            url_template=self._server.default("/api/a2a/demo"),
            decoder=json_decoder[A2ADemoOut],
            error_mapper=api_a2_a_demo_error_mapper,
            request_options=request_options,
        )


class AsyncAgentWithRawResponse(BaseRawResponse[AsyncRawClient, Server]):
    async def api_a2a_check(
        self, body: A2ACheckIn | A2ACheckInDict, *, request_options: RequestOptionsOrDict | None = None
    ) -> ApiResult[A2ACheckOut, ApiA2ACheckErrorBody]:
        """Verify a signed owner mandate and decide if a proposed deal is allowed.

        Args:
            body: The request body.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            An ``ApiResult`` holding the deserialized response or the error body."""
        return await self._client.execute(
            http_method="POST",
            url_template=self._server.default("/api/a2a/check"),
            headers=[param[UUID]("Idempotency-Key", uuid4())],
            body=json_body[A2ACheckIn | A2ACheckInDict](body),
            decoder=async_json_decoder[A2ACheckOut],
            error_mapper=api_a2_a_check_error_mapper,
            request_options=request_options,
        )

    async def api_a2a_demo(
        self, *, request_options: RequestOptionsOrDict | None = None
    ) -> ApiResult[A2ADemoOut, ApiA2ADemoErrorBody]:
        """Issue a fresh owner-signed intent mandate, plus a tampered copy of it, so the page can show live that a valid
        mandate verifies and a forged one is rejected. The key is generated per call and never leaves the server.

        Args:
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            An ``ApiResult`` holding the deserialized response or the error body."""
        return await self._client.execute(
            http_method="GET",
            url_template=self._server.default("/api/a2a/demo"),
            decoder=async_json_decoder[A2ADemoOut],
            error_mapper=api_a2_a_demo_error_mapper,
            request_options=request_options,
        )
