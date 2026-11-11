<!-- Generated file - do not edit; regenerated with the SDK. -->

# Commerce - operations

Accessor: `client.commerce` · Source: `helm_api/apis/commerce.py` · 3 operations

Each `###` block is one operation and assumes `sdk-map.md` is loaded: blocks omit what its invariants table covers and are otherwise self-contained, so chunk at block level. Signatures are the sync parsed spelling; the async and raw spellings take the same parameters (see sdk-map.md). **Type sources** names the module declaring each type an operation mentions, so resolving a body, return or error payload is a lookup rather than a search; the runtime types `RawError` and `ApiResult` are excluded.

### client.commerce.api_escrow_demo

- **Route**: `POST /api/escrow/demo`
- **Signature**: `def api_escrow_demo(body: EscrowIn | EscrowInDict, *, request_options: RequestOptionsOrDict | None = None)`
  - required, positional: `body`
- **Params**: `body` - JSON body
- **Returns (parsed)**: `EscrowOut`
- **Returns (raw)**: `ApiResult[EscrowOut, ApiEscrowDemoErrorBody]`
- **Error**: `ApiEscrowDemoErrorBody` - **Case A (typed)**
- **Error arms**: `ErrorOut` [400] · `HttpValidationError` [422] · `RawError` [anything unmapped]

| Type | Source |
| --- | --- |
| `EscrowIn` | `helm_api/models/escrow_in.py` |
| `EscrowInDict` | `helm_api/models/escrow_in.py` |
| `EscrowOut` | `helm_api/models/escrow_out.py` |
| `ApiEscrowDemoErrorBody` | `helm_api/errors/api_escrow_demo_error.py` |
| `ErrorOut` | `helm_api/models/error_out.py` |
| `HttpValidationError` | `helm_api/models/http_validation_error.py` |

### client.commerce.api_shop_buy

- **Route**: `POST /api/shop/buy`
- **Signature**: `def api_shop_buy(body: ShopBuyIn | ShopBuyInDict, *, request_options: RequestOptionsOrDict | None = None)`
  - required, positional: `body`
- **Params**: `body` - JSON body
- **Returns (parsed)**: `ShopBuyOut`
- **Returns (raw)**: `ApiResult[ShopBuyOut, ApiShopBuyErrorBody]`
- **Error**: `ApiShopBuyErrorBody` - **Case A (typed)**
- **Error arms**: `ErrorOut` [400] · `HttpValidationError` [422] · `RawError` [anything unmapped]

| Type | Source |
| --- | --- |
| `ShopBuyIn` | `helm_api/models/shop_buy_in.py` |
| `ShopBuyInDict` | `helm_api/models/shop_buy_in.py` |
| `ShopBuyOut` | `helm_api/models/shop_buy_out.py` |
| `ApiShopBuyErrorBody` | `helm_api/errors/api_shop_buy_error.py` |
| `ErrorOut` | `helm_api/models/error_out.py` |
| `HttpValidationError` | `helm_api/models/http_validation_error.py` |

### client.commerce.api_shop_search

- **Route**: `POST /api/shop/search`
- **Signature**: `def api_shop_search(body: ShopSearchIn | ShopSearchInDict, *, request_options: RequestOptionsOrDict | None = None)`
  - required, positional: `body`
- **Params**: `body` - JSON body
- **Returns (parsed)**: `ShopSearchOut`
- **Returns (raw)**: `ApiResult[ShopSearchOut, ApiShopSearchErrorBody]`
- **Error**: `ApiShopSearchErrorBody` - **Case A (typed)**
- **Error arms**: `ErrorOut` [400] · `HttpValidationError` [422] · `RawError` [anything unmapped]

| Type | Source |
| --- | --- |
| `ShopSearchIn` | `helm_api/models/shop_search_in.py` |
| `ShopSearchInDict` | `helm_api/models/shop_search_in.py` |
| `ShopSearchOut` | `helm_api/models/shop_search_out.py` |
| `ApiShopSearchErrorBody` | `helm_api/errors/api_shop_search_error.py` |
| `ErrorOut` | `helm_api/models/error_out.py` |
| `HttpValidationError` | `helm_api/models/http_validation_error.py` |

