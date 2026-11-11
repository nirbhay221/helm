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
from ..errors.api_advance_error import ApiAdvanceErrorBody, api_advance_error_mapper
from ..errors.api_invest_error import ApiInvestErrorBody, api_invest_error_mapper
from ..errors.api_quote_error import ApiQuoteErrorBody, api_quote_error_mapper
from ..errors.api_tax_error import ApiTaxErrorBody, api_tax_error_mapper
from ..models.advance_in import AdvanceIn, AdvanceInDict
from ..models.advance_out import AdvanceOut
from ..models.invest_in import InvestIn, InvestInDict
from ..models.invest_out import InvestOut
from ..models.quote_out import QuoteOut
from ..models.tax_out import TaxOut
from ..server.server import Server


class Treasury:
    def __init__(self, client: RawClient, server: Server) -> None:
        self._with_raw_response = TreasuryWithRawResponse(client, server)

    def api_advance(
        self, body: AdvanceIn | AdvanceInDict, *, request_options: RequestOptionsOrDict | None = None
    ) -> AdvanceOut:
        """A safety-capped, risk-priced advance offer against proven earnings.

        Args:
            body: The request body.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            Successful Response

        Raises:
            ApiError: Bad Request Validation Error ``error`` is ``ErrorOut | HttpValidationError | RawError``."""
        return unwrap(self._with_raw_response.api_advance(body, request_options=request_options))

    def api_invest(
        self, body: InvestIn | InvestInDict, *, request_options: RequestOptionsOrDict | None = None
    ) -> InvestOut:
        """Invest a notional amount across the basket at live prices.

        Args:
            body: The request body.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            Successful Response

        Raises:
            ApiError: Bad Request Validation Error ``error`` is ``ErrorOut | HttpValidationError | RawError``."""
        return unwrap(self._with_raw_response.api_invest(body, request_options=request_options))

    def api_quote(self, *, ticker: str | None = "SPY", request_options: RequestOptionsOrDict | None = None) -> QuoteOut:
        """Latest real market price for a ticker (Alpaca paper when keys are present, else a live-price source).

        Args:
            ticker: Ticker symbol to quote.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            Successful Response

        Raises:
            ApiError: Bad Request Validation Error ``error`` is ``ErrorOut | HttpValidationError | RawError``."""
        return unwrap(self._with_raw_response.api_quote(ticker=ticker, request_options=request_options))

    def api_tax(
        self,
        *,
        country: str | None = "US",
        gross: float | None = 0.0,
        transactions: int | None = 0,
        fees: float | None = 0.0,
        request_options: RequestOptionsOrDict | None = None,
    ) -> TaxOut:
        """A creator's reporting regime (US 1099-K thresholds or EU DAC7).

        Args:
            country: Two-letter country code.
            gross: Gross for the year.
            transactions: Transaction count.
            fees: Platform fees withheld.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            Successful Response

        Raises:
            ApiError: Bad Request Validation Error ``error`` is ``ErrorOut | HttpValidationError | RawError``."""
        return unwrap(
            self._with_raw_response.api_tax(
                country=country, gross=gross, transactions=transactions, fees=fees, request_options=request_options
            ),
        )

    @property
    def with_raw_response(self) -> TreasuryWithRawResponse:
        return self._with_raw_response


class AsyncTreasury:
    def __init__(self, client: AsyncRawClient, server: Server) -> None:
        self._with_raw_response = AsyncTreasuryWithRawResponse(client, server)

    async def api_advance(
        self, body: AdvanceIn | AdvanceInDict, *, request_options: RequestOptionsOrDict | None = None
    ) -> AdvanceOut:
        """A safety-capped, risk-priced advance offer against proven earnings.

        Args:
            body: The request body.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            Successful Response

        Raises:
            ApiError: Bad Request Validation Error ``error`` is ``ErrorOut | HttpValidationError | RawError``."""
        return unwrap(await self._with_raw_response.api_advance(body, request_options=request_options))

    async def api_invest(
        self, body: InvestIn | InvestInDict, *, request_options: RequestOptionsOrDict | None = None
    ) -> InvestOut:
        """Invest a notional amount across the basket at live prices.

        Args:
            body: The request body.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            Successful Response

        Raises:
            ApiError: Bad Request Validation Error ``error`` is ``ErrorOut | HttpValidationError | RawError``."""
        return unwrap(await self._with_raw_response.api_invest(body, request_options=request_options))

    async def api_quote(
        self, *, ticker: str | None = "SPY", request_options: RequestOptionsOrDict | None = None
    ) -> QuoteOut:
        """Latest real market price for a ticker (Alpaca paper when keys are present, else a live-price source).

        Args:
            ticker: Ticker symbol to quote.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            Successful Response

        Raises:
            ApiError: Bad Request Validation Error ``error`` is ``ErrorOut | HttpValidationError | RawError``."""
        return unwrap(await self._with_raw_response.api_quote(ticker=ticker, request_options=request_options))

    async def api_tax(
        self,
        *,
        country: str | None = "US",
        gross: float | None = 0.0,
        transactions: int | None = 0,
        fees: float | None = 0.0,
        request_options: RequestOptionsOrDict | None = None,
    ) -> TaxOut:
        """A creator's reporting regime (US 1099-K thresholds or EU DAC7).

        Args:
            country: Two-letter country code.
            gross: Gross for the year.
            transactions: Transaction count.
            fees: Platform fees withheld.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            Successful Response

        Raises:
            ApiError: Bad Request Validation Error ``error`` is ``ErrorOut | HttpValidationError | RawError``."""
        return unwrap(
            await self._with_raw_response.api_tax(
                country=country, gross=gross, transactions=transactions, fees=fees, request_options=request_options
            ),
        )

    @property
    def with_raw_response(self) -> AsyncTreasuryWithRawResponse:
        return self._with_raw_response


class TreasuryWithRawResponse(BaseRawResponse[RawClient, Server]):
    def api_advance(
        self, body: AdvanceIn | AdvanceInDict, *, request_options: RequestOptionsOrDict | None = None
    ) -> ApiResult[AdvanceOut, ApiAdvanceErrorBody]:
        """A safety-capped, risk-priced advance offer against proven earnings.

        Args:
            body: The request body.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            An ``ApiResult`` holding the deserialized response or the error body."""
        return self._client.execute(
            http_method="POST",
            url_template=self._server.default("/api/advance"),
            headers=[param[UUID]("Idempotency-Key", uuid4())],
            body=json_body[AdvanceIn | AdvanceInDict](body),
            decoder=json_decoder[AdvanceOut],
            error_mapper=api_advance_error_mapper,
            request_options=request_options,
        )

    def api_invest(
        self, body: InvestIn | InvestInDict, *, request_options: RequestOptionsOrDict | None = None
    ) -> ApiResult[InvestOut, ApiInvestErrorBody]:
        """Invest a notional amount across the basket at live prices.

        Args:
            body: The request body.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            An ``ApiResult`` holding the deserialized response or the error body."""
        return self._client.execute(
            http_method="POST",
            url_template=self._server.default("/api/invest"),
            headers=[param[UUID]("Idempotency-Key", uuid4())],
            body=json_body[InvestIn | InvestInDict](body),
            decoder=json_decoder[InvestOut],
            error_mapper=api_invest_error_mapper,
            request_options=request_options,
        )

    def api_quote(
        self, *, ticker: str | None = "SPY", request_options: RequestOptionsOrDict | None = None
    ) -> ApiResult[QuoteOut, ApiQuoteErrorBody]:
        """Latest real market price for a ticker (Alpaca paper when keys are present, else a live-price source).

        Args:
            ticker: Ticker symbol to quote.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            An ``ApiResult`` holding the deserialized response or the error body."""
        return self._client.execute(
            http_method="GET",
            url_template=self._server.default("/api/quote"),
            query_params=[param[str | None]("ticker", ticker)],
            decoder=json_decoder[QuoteOut],
            error_mapper=api_quote_error_mapper,
            request_options=request_options,
        )

    def api_tax(
        self,
        *,
        country: str | None = "US",
        gross: float | None = 0.0,
        transactions: int | None = 0,
        fees: float | None = 0.0,
        request_options: RequestOptionsOrDict | None = None,
    ) -> ApiResult[TaxOut, ApiTaxErrorBody]:
        """A creator's reporting regime (US 1099-K thresholds or EU DAC7).

        Args:
            country: Two-letter country code.
            gross: Gross for the year.
            transactions: Transaction count.
            fees: Platform fees withheld.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            An ``ApiResult`` holding the deserialized response or the error body."""
        return self._client.execute(
            http_method="GET",
            url_template=self._server.default("/api/tax"),
            query_params=[
                param[str | None]("country", country),
                param[float | None]("gross", gross),
                param[int | None]("transactions", transactions),
                param[float | None]("fees", fees),
            ],
            decoder=json_decoder[TaxOut],
            error_mapper=api_tax_error_mapper,
            request_options=request_options,
        )


class AsyncTreasuryWithRawResponse(BaseRawResponse[AsyncRawClient, Server]):
    async def api_advance(
        self, body: AdvanceIn | AdvanceInDict, *, request_options: RequestOptionsOrDict | None = None
    ) -> ApiResult[AdvanceOut, ApiAdvanceErrorBody]:
        """A safety-capped, risk-priced advance offer against proven earnings.

        Args:
            body: The request body.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            An ``ApiResult`` holding the deserialized response or the error body."""
        return await self._client.execute(
            http_method="POST",
            url_template=self._server.default("/api/advance"),
            headers=[param[UUID]("Idempotency-Key", uuid4())],
            body=json_body[AdvanceIn | AdvanceInDict](body),
            decoder=async_json_decoder[AdvanceOut],
            error_mapper=api_advance_error_mapper,
            request_options=request_options,
        )

    async def api_invest(
        self, body: InvestIn | InvestInDict, *, request_options: RequestOptionsOrDict | None = None
    ) -> ApiResult[InvestOut, ApiInvestErrorBody]:
        """Invest a notional amount across the basket at live prices.

        Args:
            body: The request body.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            An ``ApiResult`` holding the deserialized response or the error body."""
        return await self._client.execute(
            http_method="POST",
            url_template=self._server.default("/api/invest"),
            headers=[param[UUID]("Idempotency-Key", uuid4())],
            body=json_body[InvestIn | InvestInDict](body),
            decoder=async_json_decoder[InvestOut],
            error_mapper=api_invest_error_mapper,
            request_options=request_options,
        )

    async def api_quote(
        self, *, ticker: str | None = "SPY", request_options: RequestOptionsOrDict | None = None
    ) -> ApiResult[QuoteOut, ApiQuoteErrorBody]:
        """Latest real market price for a ticker (Alpaca paper when keys are present, else a live-price source).

        Args:
            ticker: Ticker symbol to quote.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            An ``ApiResult`` holding the deserialized response or the error body."""
        return await self._client.execute(
            http_method="GET",
            url_template=self._server.default("/api/quote"),
            query_params=[param[str | None]("ticker", ticker)],
            decoder=async_json_decoder[QuoteOut],
            error_mapper=api_quote_error_mapper,
            request_options=request_options,
        )

    async def api_tax(
        self,
        *,
        country: str | None = "US",
        gross: float | None = 0.0,
        transactions: int | None = 0,
        fees: float | None = 0.0,
        request_options: RequestOptionsOrDict | None = None,
    ) -> ApiResult[TaxOut, ApiTaxErrorBody]:
        """A creator's reporting regime (US 1099-K thresholds or EU DAC7).

        Args:
            country: Two-letter country code.
            gross: Gross for the year.
            transactions: Transaction count.
            fees: Platform fees withheld.
            request_options: Per-call overrides for this one request, such as a timeout, extra headers, or its retry
                count and statuses.

        Returns:
            An ``ApiResult`` holding the deserialized response or the error body."""
        return await self._client.execute(
            http_method="GET",
            url_template=self._server.default("/api/tax"),
            query_params=[
                param[str | None]("country", country),
                param[float | None]("gross", gross),
                param[int | None]("transactions", transactions),
                param[float | None]("fees", fees),
            ],
            decoder=async_json_decoder[TaxOut],
            error_mapper=api_tax_error_mapper,
            request_options=request_options,
        )
