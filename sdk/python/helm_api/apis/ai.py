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
from ..errors.api_policy_error import ApiPolicyErrorBody, api_policy_error_mapper
from ..errors.api_signal_error import ApiSignalErrorBody, api_signal_error_mapper
from ..models.policy_in import PolicyIn, PolicyInDict
from ..models.policy_out import PolicyOut
from ..models.signal_in import SignalIn, SignalInDict
from ..models.signal_out import SignalOut
from ..server.server import Server


class Ai:
    def __init__(self, client: RawClient, server: Server) -> None:
        self._with_raw_response = AiWithRawResponse(client, server)

    def api_policy(
        self, body: PolicyIn | PolicyInDict, *, request_options: RequestOptionsOrDict | None = None
    ) -> PolicyOut:
        """Compile an English treasury policy into objective weights and hard constraints with the live model.

        Args:
            body: The request body.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            Successful Response

        Raises:
            ApiError: Bad Request Validation Error ``error`` is ``ErrorOut | HttpValidationError | RawError``."""
        return unwrap(self._with_raw_response.api_policy(body, request_options=request_options))

    def api_signal(
        self, body: SignalIn | SignalInDict, *, request_options: RequestOptionsOrDict | None = None
    ) -> SignalOut:
        """Read an operational signal into a bounded, per-period forecast adjustment (live model).

        Args:
            body: The request body.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            Successful Response

        Raises:
            ApiError: Bad Request Validation Error ``error`` is ``ErrorOut | HttpValidationError | RawError``."""
        return unwrap(self._with_raw_response.api_signal(body, request_options=request_options))

    @property
    def with_raw_response(self) -> AiWithRawResponse:
        return self._with_raw_response


class AsyncAi:
    def __init__(self, client: AsyncRawClient, server: Server) -> None:
        self._with_raw_response = AsyncAiWithRawResponse(client, server)

    async def api_policy(
        self, body: PolicyIn | PolicyInDict, *, request_options: RequestOptionsOrDict | None = None
    ) -> PolicyOut:
        """Compile an English treasury policy into objective weights and hard constraints with the live model.

        Args:
            body: The request body.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            Successful Response

        Raises:
            ApiError: Bad Request Validation Error ``error`` is ``ErrorOut | HttpValidationError | RawError``."""
        return unwrap(await self._with_raw_response.api_policy(body, request_options=request_options))

    async def api_signal(
        self, body: SignalIn | SignalInDict, *, request_options: RequestOptionsOrDict | None = None
    ) -> SignalOut:
        """Read an operational signal into a bounded, per-period forecast adjustment (live model).

        Args:
            body: The request body.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            Successful Response

        Raises:
            ApiError: Bad Request Validation Error ``error`` is ``ErrorOut | HttpValidationError | RawError``."""
        return unwrap(await self._with_raw_response.api_signal(body, request_options=request_options))

    @property
    def with_raw_response(self) -> AsyncAiWithRawResponse:
        return self._with_raw_response


class AiWithRawResponse(BaseRawResponse[RawClient, Server]):
    def api_policy(
        self, body: PolicyIn | PolicyInDict, *, request_options: RequestOptionsOrDict | None = None
    ) -> ApiResult[PolicyOut, ApiPolicyErrorBody]:
        """Compile an English treasury policy into objective weights and hard constraints with the live model.

        Args:
            body: The request body.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            An ``ApiResult`` holding the deserialized response or the error body."""
        return self._client.execute(
            http_method="POST",
            url_template=self._server.default("/api/policy"),
            headers=[param[UUID]("Idempotency-Key", uuid4())],
            body=json_body[PolicyIn | PolicyInDict](body),
            decoder=json_decoder[PolicyOut],
            error_mapper=api_policy_error_mapper,
            request_options=request_options,
        )

    def api_signal(
        self, body: SignalIn | SignalInDict, *, request_options: RequestOptionsOrDict | None = None
    ) -> ApiResult[SignalOut, ApiSignalErrorBody]:
        """Read an operational signal into a bounded, per-period forecast adjustment (live model).

        Args:
            body: The request body.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            An ``ApiResult`` holding the deserialized response or the error body."""
        return self._client.execute(
            http_method="POST",
            url_template=self._server.default("/api/signal"),
            headers=[param[UUID]("Idempotency-Key", uuid4())],
            body=json_body[SignalIn | SignalInDict](body),
            decoder=json_decoder[SignalOut],
            error_mapper=api_signal_error_mapper,
            request_options=request_options,
        )


class AsyncAiWithRawResponse(BaseRawResponse[AsyncRawClient, Server]):
    async def api_policy(
        self, body: PolicyIn | PolicyInDict, *, request_options: RequestOptionsOrDict | None = None
    ) -> ApiResult[PolicyOut, ApiPolicyErrorBody]:
        """Compile an English treasury policy into objective weights and hard constraints with the live model.

        Args:
            body: The request body.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            An ``ApiResult`` holding the deserialized response or the error body."""
        return await self._client.execute(
            http_method="POST",
            url_template=self._server.default("/api/policy"),
            headers=[param[UUID]("Idempotency-Key", uuid4())],
            body=json_body[PolicyIn | PolicyInDict](body),
            decoder=async_json_decoder[PolicyOut],
            error_mapper=api_policy_error_mapper,
            request_options=request_options,
        )

    async def api_signal(
        self, body: SignalIn | SignalInDict, *, request_options: RequestOptionsOrDict | None = None
    ) -> ApiResult[SignalOut, ApiSignalErrorBody]:
        """Read an operational signal into a bounded, per-period forecast adjustment (live model).

        Args:
            body: The request body.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            An ``ApiResult`` holding the deserialized response or the error body."""
        return await self._client.execute(
            http_method="POST",
            url_template=self._server.default("/api/signal"),
            headers=[param[UUID]("Idempotency-Key", uuid4())],
            body=json_body[SignalIn | SignalInDict](body),
            decoder=async_json_decoder[SignalOut],
            error_mapper=api_signal_error_mapper,
            request_options=request_options,
        )
