<!-- Generated file - do not edit; regenerated with the SDK. -->

# Proofs - operations

Accessor: `client.proofs` · Source: `helm_api/apis/proofs.py` · 2 operations

Each `###` block is one operation and assumes `sdk-map.md` is loaded: blocks omit what its invariants table covers and are otherwise self-contained, so chunk at block level. Signatures are the sync parsed spelling; the async and raw spellings take the same parameters (see sdk-map.md). **Type sources** names the module declaring each type an operation mentions, so resolving a body, return or error payload is a lookup rather than a search; the runtime types `RawError` and `ApiResult` are excluded.

### client.proofs.api_reserves_prove

- **Route**: `POST /api/reserves/prove`
- **Signature**: `def api_reserves_prove(body: ReservesIn | ReservesInDict, *, request_options: RequestOptionsOrDict | None = None)`
  - required, positional: `body`
- **Params**: `body` - JSON body
- **Returns (parsed)**: `ReservesOut`
- **Returns (raw)**: `ApiResult[ReservesOut, ApiReservesProveErrorBody]`
- **Error**: `ApiReservesProveErrorBody` - **Case A (typed)**
- **Error arms**: `ErrorOut` [400] · `HttpValidationError` [422] · `RawError` [anything unmapped]

| Type | Source |
| --- | --- |
| `ReservesIn` | `helm_api/models/reserves_in.py` |
| `ReservesInDict` | `helm_api/models/reserves_in.py` |
| `ReservesOut` | `helm_api/models/reserves_out.py` |
| `ApiReservesProveErrorBody` | `helm_api/errors/api_reserves_prove_error.py` |
| `ErrorOut` | `helm_api/models/error_out.py` |
| `HttpValidationError` | `helm_api/models/http_validation_error.py` |

### client.proofs.api_verify_mandate

- **Route**: `POST /api/verify/mandate`
- **Signature**: `def api_verify_mandate(body: VerifyMandateIn | VerifyMandateInDict, *, request_options: RequestOptionsOrDict | None = None)`
  - required, positional: `body`
- **Params**: `body` - JSON body
- **Returns (parsed)**: `VerifyMandateOut`
- **Returns (raw)**: `ApiResult[VerifyMandateOut, ApiVerifyMandateErrorBody]`
- **Error**: `ApiVerifyMandateErrorBody` - **Case A (typed)**
- **Error arms**: `ErrorOut` [400] · `HttpValidationError` [422] · `RawError` [anything unmapped]

| Type | Source |
| --- | --- |
| `VerifyMandateIn` | `helm_api/models/verify_mandate_in.py` |
| `VerifyMandateInDict` | `helm_api/models/verify_mandate_in.py` |
| `VerifyMandateOut` | `helm_api/models/verify_mandate_out.py` |
| `ApiVerifyMandateErrorBody` | `helm_api/errors/api_verify_mandate_error.py` |
| `ErrorOut` | `helm_api/models/error_out.py` |
| `HttpValidationError` | `helm_api/models/http_validation_error.py` |

