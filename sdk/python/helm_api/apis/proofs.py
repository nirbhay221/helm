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
from ..errors.api_reserves_prove_error import ApiReservesProveErrorBody, api_reserves_prove_error_mapper
from ..errors.api_verify_mandate_error import ApiVerifyMandateErrorBody, api_verify_mandate_error_mapper
from ..models.reserves_in import ReservesIn, ReservesInDict
from ..models.reserves_out import ReservesOut
from ..models.verify_mandate_in import VerifyMandateIn, VerifyMandateInDict
from ..models.verify_mandate_out import VerifyMandateOut
from ..server.server import Server


class Proofs:
    def __init__(self, client: RawClient, server: Server) -> None:
        self._with_raw_response = ProofsWithRawResponse(client, server)

    def api_reserves_prove(
        self, body: ReservesIn | ReservesInDict, *, request_options: RequestOptionsOrDict | None = None
    ) -> ReservesOut:
        """Prove in zero knowledge that the safety fund covers its liabilities without revealing any balance. Returns
        only the verification outcome and the proof shape; the amounts never leave the server.

        Args:
            body: The request body.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            Successful Response

        Raises:
            ApiError: Bad Request Validation Error ``error`` is ``ErrorOut | HttpValidationError | RawError``."""
        return unwrap(self._with_raw_response.api_reserves_prove(body, request_options=request_options))

    def api_verify_mandate(
        self, body: VerifyMandateIn | VerifyMandateInDict, *, request_options: RequestOptionsOrDict | None = None
    ) -> VerifyMandateOut:
        """Prove with Z3 that an agent's signed mandate is budget-bounded for ANY sequence of deals (an unbounded
        inductive-invariant proof), show the guard set is necessary via a counterexample, and return an ES256-signed
        authorization verdict. A forge flag tampers the mandate to show it is rejected.

        Args:
            body: The request body.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            Successful Response

        Raises:
            ApiError: Bad Request Validation Error ``error`` is ``ErrorOut | HttpValidationError | RawError``."""
        return unwrap(self._with_raw_response.api_verify_mandate(body, request_options=request_options))

    @property
    def with_raw_response(self) -> ProofsWithRawResponse:
        return self._with_raw_response


class AsyncProofs:
    def __init__(self, client: AsyncRawClient, server: Server) -> None:
        self._with_raw_response = AsyncProofsWithRawResponse(client, server)

    async def api_reserves_prove(
        self, body: ReservesIn | ReservesInDict, *, request_options: RequestOptionsOrDict | None = None
    ) -> ReservesOut:
        """Prove in zero knowledge that the safety fund covers its liabilities without revealing any balance. Returns
        only the verification outcome and the proof shape; the amounts never leave the server.

        Args:
            body: The request body.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            Successful Response

        Raises:
            ApiError: Bad Request Validation Error ``error`` is ``ErrorOut | HttpValidationError | RawError``."""
        return unwrap(await self._with_raw_response.api_reserves_prove(body, request_options=request_options))

    async def api_verify_mandate(
        self, body: VerifyMandateIn | VerifyMandateInDict, *, request_options: RequestOptionsOrDict | None = None
    ) -> VerifyMandateOut:
        """Prove with Z3 that an agent's signed mandate is budget-bounded for ANY sequence of deals (an unbounded
        inductive-invariant proof), show the guard set is necessary via a counterexample, and return an ES256-signed
        authorization verdict. A forge flag tampers the mandate to show it is rejected.

        Args:
            body: The request body.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            Successful Response

        Raises:
            ApiError: Bad Request Validation Error ``error`` is ``ErrorOut | HttpValidationError | RawError``."""
        return unwrap(await self._with_raw_response.api_verify_mandate(body, request_options=request_options))

    @property
    def with_raw_response(self) -> AsyncProofsWithRawResponse:
        return self._with_raw_response


class ProofsWithRawResponse(BaseRawResponse[RawClient, Server]):
    def api_reserves_prove(
        self, body: ReservesIn | ReservesInDict, *, request_options: RequestOptionsOrDict | None = None
    ) -> ApiResult[ReservesOut, ApiReservesProveErrorBody]:
        """Prove in zero knowledge that the safety fund covers its liabilities without revealing any balance. Returns
        only the verification outcome and the proof shape; the amounts never leave the server.

        Args:
            body: The request body.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            An ``ApiResult`` holding the deserialized response or the error body."""
        return self._client.execute(
            http_method="POST",
            url_template=self._server.default("/api/reserves/prove"),
            headers=[param[UUID]("Idempotency-Key", uuid4())],
            body=json_body[ReservesIn | ReservesInDict](body),
            decoder=json_decoder[ReservesOut],
            error_mapper=api_reserves_prove_error_mapper,
            request_options=request_options,
        )

    def api_verify_mandate(
        self, body: VerifyMandateIn | VerifyMandateInDict, *, request_options: RequestOptionsOrDict | None = None
    ) -> ApiResult[VerifyMandateOut, ApiVerifyMandateErrorBody]:
        """Prove with Z3 that an agent's signed mandate is budget-bounded for ANY sequence of deals (an unbounded
        inductive-invariant proof), show the guard set is necessary via a counterexample, and return an ES256-signed
        authorization verdict. A forge flag tampers the mandate to show it is rejected.

        Args:
            body: The request body.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            An ``ApiResult`` holding the deserialized response or the error body."""
        return self._client.execute(
            http_method="POST",
            url_template=self._server.default("/api/verify/mandate"),
            headers=[param[UUID]("Idempotency-Key", uuid4())],
            body=json_body[VerifyMandateIn | VerifyMandateInDict](body),
            decoder=json_decoder[VerifyMandateOut],
            error_mapper=api_verify_mandate_error_mapper,
            request_options=request_options,
        )


class AsyncProofsWithRawResponse(BaseRawResponse[AsyncRawClient, Server]):
    async def api_reserves_prove(
        self, body: ReservesIn | ReservesInDict, *, request_options: RequestOptionsOrDict | None = None
    ) -> ApiResult[ReservesOut, ApiReservesProveErrorBody]:
        """Prove in zero knowledge that the safety fund covers its liabilities without revealing any balance. Returns
        only the verification outcome and the proof shape; the amounts never leave the server.

        Args:
            body: The request body.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            An ``ApiResult`` holding the deserialized response or the error body."""
        return await self._client.execute(
            http_method="POST",
            url_template=self._server.default("/api/reserves/prove"),
            headers=[param[UUID]("Idempotency-Key", uuid4())],
            body=json_body[ReservesIn | ReservesInDict](body),
            decoder=async_json_decoder[ReservesOut],
            error_mapper=api_reserves_prove_error_mapper,
            request_options=request_options,
        )

    async def api_verify_mandate(
        self, body: VerifyMandateIn | VerifyMandateInDict, *, request_options: RequestOptionsOrDict | None = None
    ) -> ApiResult[VerifyMandateOut, ApiVerifyMandateErrorBody]:
        """Prove with Z3 that an agent's signed mandate is budget-bounded for ANY sequence of deals (an unbounded
        inductive-invariant proof), show the guard set is necessary via a counterexample, and return an ES256-signed
        authorization verdict. A forge flag tampers the mandate to show it is rejected.

        Args:
            body: The request body.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            An ``ApiResult`` holding the deserialized response or the error body."""
        return await self._client.execute(
            http_method="POST",
            url_template=self._server.default("/api/verify/mandate"),
            headers=[param[UUID]("Idempotency-Key", uuid4())],
            body=json_body[VerifyMandateIn | VerifyMandateInDict](body),
            decoder=async_json_decoder[VerifyMandateOut],
            error_mapper=api_verify_mandate_error_mapper,
            request_options=request_options,
        )
