<!-- Generated file - do not edit; regenerated with the SDK. -->

# Dashboard - operations

Accessor: `client.dashboard` · Source: `helm_api/apis/dashboard.py` · 3 operations

Each `###` block is one operation and assumes `sdk-map.md` is loaded: blocks omit what its invariants table covers and are otherwise self-contained, so chunk at block level. Signatures are the sync parsed spelling; the async and raw spellings take the same parameters (see sdk-map.md). **Type sources** names the module declaring each type an operation mentions, so resolving a body, return or error payload is a lookup rather than a search; the runtime types `RawError` and `ApiResult` are excluded, and an operation with no table mentions nothing but builtins and those.

### client.dashboard.data

- **Route**: `GET /api/data`
- **Signature**: `def data(*, request_options: RequestOptionsOrDict | None = None)`
- **Returns (parsed)**: `Any`
- **Returns (raw)**: `ApiResult[Any, RawError]`
- **Error**: `RawError` - **Case B**

### client.dashboard.healthz

- **Route**: `GET /healthz`
- **Signature**: `def healthz(*, request_options: RequestOptionsOrDict | None = None)`
- **Returns (parsed)**: `str`
- **Returns (raw)**: `ApiResult[str, RawError]`
- **Error**: `RawError` - **Case B**

### client.dashboard.index

- **Route**: `GET /`
- **Signature**: `def index(*, request_options: RequestOptionsOrDict | None = None)`
- **Returns (parsed)**: `None`
- **Returns (raw)**: `ApiResult[None, RawError]`
- **Error**: `RawError` - **Case B**

