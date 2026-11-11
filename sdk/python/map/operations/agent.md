<!-- Generated file - do not edit; regenerated with the SDK. -->

# Agent - operations

Accessor: `client.agent` · Source: `helm_api/apis/agent.py` · 2 operations

Each `###` block is one operation and assumes `sdk-map.md` is loaded: blocks omit what its invariants table covers and are otherwise self-contained, so chunk at block level. Signatures are the sync parsed spelling; the async and raw spellings take the same parameters (see sdk-map.md). **Type sources** names the module declaring each type an operation mentions, so resolving a body, return or error payload is a lookup rather than a search; the runtime types `RawError` and `ApiResult` are excluded.

### client.agent.api_a2a_check

- **Route**: `POST /api/a2a/check`
- **Signature**: `def api_a2a_check(body: A2ACheckIn | A2ACheckInDict, *, request_options: RequestOptionsOrDict | None = None)`
  - required, positional: `body`
- **Params**: `body` - JSON body
- **Returns (parsed)**: `A2ACheckOut`
- **Returns (raw)**: `ApiResult[A2ACheckOut, ApiA2ACheckErrorBody]`
- **Error**: `ApiA2ACheckErrorBody` - **Case A (typed)**
- **Error arms**: `ErrorOut` [400] · `HttpValidationError` [422] · `RawError` [anything unmapped]

| Type | Source |
| --- | --- |
| `A2ACheckIn` | `helm_api/models/a2_a_check_in.py` |
| `A2ACheckInDict` | `helm_api/models/a2_a_check_in.py` |
| `A2ACheckOut` | `helm_api/models/a2_a_check_out.py` |
| `ApiA2ACheckErrorBody` | `helm_api/errors/api_a2_a_check_error.py` |
| `ErrorOut` | `helm_api/models/error_out.py` |
| `HttpValidationError` | `helm_api/models/http_validation_error.py` |

### client.agent.api_a2a_demo

- **Route**: `GET /api/a2a/demo`
- **Signature**: `def api_a2a_demo(*, request_options: RequestOptionsOrDict | None = None)`
- **Returns (parsed)**: `A2ADemoOut`
- **Returns (raw)**: `ApiResult[A2ADemoOut, ApiA2ADemoErrorBody]`
- **Error**: `ApiA2ADemoErrorBody` - **Case A (typed)**
- **Error arms**: `ErrorOut` [400] · `RawError` [anything unmapped]

| Type | Source |
| --- | --- |
| `A2ADemoOut` | `helm_api/models/a2_a_demo_out.py` |
| `ApiA2ADemoErrorBody` | `helm_api/errors/api_a2_a_demo_error.py` |
| `ErrorOut` | `helm_api/models/error_out.py` |

