<!-- Generated file - do not edit; regenerated with the SDK. -->

# Pooling - operations

Accessor: `client.pooling` · Source: `helm_api/apis/pooling.py` · 2 operations

Each `###` block is one operation and assumes `sdk-map.md` is loaded: blocks omit what its invariants table covers and are otherwise self-contained, so chunk at block level. Signatures are the sync parsed spelling; the async and raw spellings take the same parameters (see sdk-map.md). **Type sources** names the module declaring each type an operation mentions, so resolving a body, return or error payload is a lookup rather than a search; the runtime types `RawError` and `ApiResult` are excluded.

### client.pooling.api_pool_groupbuy

- **Route**: `POST /api/pool/groupbuy`
- **Signature**: `def api_pool_groupbuy(body: GroupBuyIn | GroupBuyInDict, *, request_options: RequestOptionsOrDict | None = None)`
  - required, positional: `body`
- **Params**: `body` - JSON body
- **Returns (parsed)**: `GroupBuyOut`
- **Returns (raw)**: `ApiResult[GroupBuyOut, ApiPoolGroupbuyErrorBody]`
- **Error**: `ApiPoolGroupbuyErrorBody` - **Case A (typed)**
- **Error arms**: `ErrorOut` [400] · `HttpValidationError` [422] · `RawError` [anything unmapped]

| Type | Source |
| --- | --- |
| `GroupBuyIn` | `helm_api/models/group_buy_in.py` |
| `GroupBuyInDict` | `helm_api/models/group_buy_in.py` |
| `GroupBuyOut` | `helm_api/models/group_buy_out.py` |
| `ApiPoolGroupbuyErrorBody` | `helm_api/errors/api_pool_groupbuy_error.py` |
| `ErrorOut` | `helm_api/models/error_out.py` |
| `HttpValidationError` | `helm_api/models/http_validation_error.py` |

### client.pooling.api_pool_invest

- **Route**: `POST /api/pool/invest`
- **Signature**: `def api_pool_invest(body: PoolInvestIn | PoolInvestInDict, *, request_options: RequestOptionsOrDict | None = None)`
  - required, positional: `body`
- **Params**: `body` - JSON body
- **Returns (parsed)**: `PoolInvestOut`
- **Returns (raw)**: `ApiResult[PoolInvestOut, ApiPoolInvestErrorBody]`
- **Error**: `ApiPoolInvestErrorBody` - **Case A (typed)**
- **Error arms**: `ErrorOut` [400] · `HttpValidationError` [422] · `RawError` [anything unmapped]

| Type | Source |
| --- | --- |
| `PoolInvestIn` | `helm_api/models/pool_invest_in.py` |
| `PoolInvestInDict` | `helm_api/models/pool_invest_in.py` |
| `PoolInvestOut` | `helm_api/models/pool_invest_out.py` |
| `ApiPoolInvestErrorBody` | `helm_api/errors/api_pool_invest_error.py` |
| `ErrorOut` | `helm_api/models/error_out.py` |
| `HttpValidationError` | `helm_api/models/http_validation_error.py` |

