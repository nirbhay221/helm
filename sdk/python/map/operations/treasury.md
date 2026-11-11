<!-- Generated file - do not edit; regenerated with the SDK. -->

# Treasury - operations

Accessor: `client.treasury` · Source: `helm_api/apis/treasury.py` · 4 operations

Each `###` block is one operation and assumes `sdk-map.md` is loaded: blocks omit what its invariants table covers and are otherwise self-contained, so chunk at block level. Signatures are the sync parsed spelling; the async and raw spellings take the same parameters (see sdk-map.md). **Type sources** names the module declaring each type an operation mentions, so resolving a body, return or error payload is a lookup rather than a search; the runtime types `RawError` and `ApiResult` are excluded.

### client.treasury.api_advance

- **Route**: `POST /api/advance`
- **Signature**: `def api_advance(body: AdvanceIn | AdvanceInDict, *, request_options: RequestOptionsOrDict | None = None)`
  - required, positional: `body`
- **Params**: `body` - JSON body
- **Returns (parsed)**: `AdvanceOut`
- **Returns (raw)**: `ApiResult[AdvanceOut, ApiAdvanceErrorBody]`
- **Error**: `ApiAdvanceErrorBody` - **Case A (typed)**
- **Error arms**: `ErrorOut` [400] · `HttpValidationError` [422] · `RawError` [anything unmapped]

| Type | Source |
| --- | --- |
| `AdvanceIn` | `helm_api/models/advance_in.py` |
| `AdvanceInDict` | `helm_api/models/advance_in.py` |
| `AdvanceOut` | `helm_api/models/advance_out.py` |
| `ApiAdvanceErrorBody` | `helm_api/errors/api_advance_error.py` |
| `ErrorOut` | `helm_api/models/error_out.py` |
| `HttpValidationError` | `helm_api/models/http_validation_error.py` |

### client.treasury.api_invest

- **Route**: `POST /api/invest`
- **Signature**: `def api_invest(body: InvestIn | InvestInDict, *, request_options: RequestOptionsOrDict | None = None)`
  - required, positional: `body`
- **Params**: `body` - JSON body
- **Returns (parsed)**: `InvestOut`
- **Returns (raw)**: `ApiResult[InvestOut, ApiInvestErrorBody]`
- **Error**: `ApiInvestErrorBody` - **Case A (typed)**
- **Error arms**: `ErrorOut` [400] · `HttpValidationError` [422] · `RawError` [anything unmapped]

| Type | Source |
| --- | --- |
| `InvestIn` | `helm_api/models/invest_in.py` |
| `InvestInDict` | `helm_api/models/invest_in.py` |
| `InvestOut` | `helm_api/models/invest_out.py` |
| `ApiInvestErrorBody` | `helm_api/errors/api_invest_error.py` |
| `ErrorOut` | `helm_api/models/error_out.py` |
| `HttpValidationError` | `helm_api/models/http_validation_error.py` |

### client.treasury.api_quote

- **Route**: `GET /api/quote`
- **Signature**: `def api_quote(*, ticker: str | None = "SPY", request_options: RequestOptionsOrDict | None = None)`
- **Params**: `ticker` - query
- **Returns (parsed)**: `QuoteOut`
- **Returns (raw)**: `ApiResult[QuoteOut, ApiQuoteErrorBody]`
- **Error**: `ApiQuoteErrorBody` - **Case A (typed)**
- **Error arms**: `ErrorOut` [400] · `HttpValidationError` [422] · `RawError` [anything unmapped]

| Type | Source |
| --- | --- |
| `QuoteOut` | `helm_api/models/quote_out.py` |
| `ApiQuoteErrorBody` | `helm_api/errors/api_quote_error.py` |
| `ErrorOut` | `helm_api/models/error_out.py` |
| `HttpValidationError` | `helm_api/models/http_validation_error.py` |

### client.treasury.api_tax

- **Route**: `GET /api/tax`
- **Signature**: `def api_tax(*, country: str | None = "US", gross: float | None = 0.0, transactions: int | None = 0, fees: float | None = 0.0, request_options: RequestOptionsOrDict | None = None)`
- **Params**: `country` - query · `gross` - query · `transactions` - query · `fees` - query
- **Returns (parsed)**: `TaxOut`
- **Returns (raw)**: `ApiResult[TaxOut, ApiTaxErrorBody]`
- **Error**: `ApiTaxErrorBody` - **Case A (typed)**
- **Error arms**: `ErrorOut` [400] · `HttpValidationError` [422] · `RawError` [anything unmapped]

| Type | Source |
| --- | --- |
| `TaxOut` | `helm_api/models/tax_out.py` |
| `ApiTaxErrorBody` | `helm_api/errors/api_tax_error.py` |
| `ErrorOut` | `helm_api/models/error_out.py` |
| `HttpValidationError` | `helm_api/models/http_validation_error.py` |

