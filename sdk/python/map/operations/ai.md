<!-- Generated file - do not edit; regenerated with the SDK. -->

# Ai - operations

Accessor: `client.ai` · Source: `helm_api/apis/ai.py` · 2 operations

Each `###` block is one operation and assumes `sdk-map.md` is loaded: blocks omit what its invariants table covers and are otherwise self-contained, so chunk at block level. Signatures are the sync parsed spelling; the async and raw spellings take the same parameters (see sdk-map.md). **Type sources** names the module declaring each type an operation mentions, so resolving a body, return or error payload is a lookup rather than a search; the runtime types `RawError` and `ApiResult` are excluded.

### client.ai.api_policy

- **Route**: `POST /api/policy`
- **Signature**: `def api_policy(body: PolicyIn | PolicyInDict, *, request_options: RequestOptionsOrDict | None = None)`
  - required, positional: `body`
- **Params**: `body` - JSON body
- **Returns (parsed)**: `PolicyOut`
- **Returns (raw)**: `ApiResult[PolicyOut, ApiPolicyErrorBody]`
- **Error**: `ApiPolicyErrorBody` - **Case A (typed)**
- **Error arms**: `ErrorOut` [400] · `HttpValidationError` [422] · `RawError` [anything unmapped]

| Type | Source |
| --- | --- |
| `PolicyIn` | `helm_api/models/policy_in.py` |
| `PolicyInDict` | `helm_api/models/policy_in.py` |
| `PolicyOut` | `helm_api/models/policy_out.py` |
| `ApiPolicyErrorBody` | `helm_api/errors/api_policy_error.py` |
| `ErrorOut` | `helm_api/models/error_out.py` |
| `HttpValidationError` | `helm_api/models/http_validation_error.py` |

### client.ai.api_signal

- **Route**: `POST /api/signal`
- **Signature**: `def api_signal(body: SignalIn | SignalInDict, *, request_options: RequestOptionsOrDict | None = None)`
  - required, positional: `body`
- **Params**: `body` - JSON body
- **Returns (parsed)**: `SignalOut`
- **Returns (raw)**: `ApiResult[SignalOut, ApiSignalErrorBody]`
- **Error**: `ApiSignalErrorBody` - **Case A (typed)**
- **Error arms**: `ErrorOut` [400] · `HttpValidationError` [422] · `RawError` [anything unmapped]

| Type | Source |
| --- | --- |
| `SignalIn` | `helm_api/models/signal_in.py` |
| `SignalInDict` | `helm_api/models/signal_in.py` |
| `SignalOut` | `helm_api/models/signal_out.py` |
| `ApiSignalErrorBody` | `helm_api/errors/api_signal_error.py` |
| `ErrorOut` | `helm_api/models/error_out.py` |
| `HttpValidationError` | `helm_api/models/http_validation_error.py` |

