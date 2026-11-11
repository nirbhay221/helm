# Raw Reference

**Raw** endpoints, reached through `with_raw_response`, return `ApiResult[T, E]` and never raise for an API error. For the parsed endpoints, see [API Reference](api-reference.md).

> Source: [HelmApiClient](helm_api/client.py)

## Agent

> Source: [Agent](helm_api/apis/agent.py)

<details>
<summary><code>def api_a2a_check(body: A2ACheckIn | A2ACheckInDict, *, request_options: RequestOptionsOrDict | None = None) -> ApiResult[A2ACheckOut, ApiA2ACheckErrorBody]</code></summary>

<dl>
<dd>

### Description

<dl>
<dd>

Verify a signed owner mandate and decide if a proposed deal is allowed.

</dd>
</dl>

### Usage

<dl>
<dd>

**Sync**

```python
result = client.agent.with_raw_response.api_a2a_check(A2ACheckIn())
match result:
    case Success(payload=payload):
        ...  # TODO: Handle 'payload' of type A2ACheckOut
    case Failure(error=error):
        ...  # TODO: Handle 'error' of type ApiA2ACheckErrorBody
```

**Async**

```python
result = await async_client.agent.with_raw_response.api_a2a_check(A2ACheckIn())
match result:
    case Success(payload=payload):
        ...  # TODO: Handle 'payload' of type A2ACheckOut
    case Failure(error=error):
        ...  # TODO: Handle 'error' of type ApiA2ACheckErrorBody
```

</dd>
</dl>

### Parameters

<dl>
<dd>

| Name | Type | Description |
| --- | --- | --- |
| <code>body</code> | <code>[A2ACheckIn](helm_api/models/a2_a_check_in.py) \| [A2ACheckInDict](helm_api/models/a2_a_check_in.py)</code> | The request body. |
| <code>request_options</code> | <code>[RequestOptionsOrDict](helm_api/core/request_options.py) \| None</code> | Per-call overrides for this one request, such as a timeout, extra headers, or its retry count and statuses. |

</dd>
</dl>

### Response

<dl>
<dd>

**Returns**: <code>[ApiResult](helm_api/core/results.py)&#91;[A2ACheckOut](helm_api/models/a2_a_check_out.py), [ApiA2ACheckErrorBody](helm_api/errors/api_a2_a_check_error.py)&#93;</code>

**On `Success`**: `payload` is <code>[A2ACheckOut](helm_api/models/a2_a_check_out.py)</code> -- Successful Response

**On `Failure`**: `error` is <code>[ApiA2ACheckErrorBody](helm_api/errors/api_a2_a_check_error.py)</code>

Mapped in first-match order -- an earlier row wins over a later range that also covers the status:

| Status | `error` is |
| --- | --- |
| 400 | <code>[ErrorOut](helm_api/models/error_out.py)</code> |
| 422 | <code>[HttpValidationError](helm_api/models/http_validation_error.py)</code> |
| anything unmapped | <code>[RawError](helm_api/core/results.py)</code> |

</dd>
</dl>

</dd>
</dl>

</details>

<details>
<summary><code>def api_a2a_demo(*, request_options: RequestOptionsOrDict | None = None) -> ApiResult[A2ADemoOut, ApiA2ADemoErrorBody]</code></summary>

<dl>
<dd>

### Description

<dl>
<dd>

Issue a fresh owner-signed intent mandate, plus a tampered copy of it, so the page can
show live that a valid mandate verifies and a forged one is rejected. The key is generated
per call and never leaves the server.

</dd>
</dl>

### Usage

<dl>
<dd>

**Sync**

```python
result = client.agent.with_raw_response.api_a2a_demo()
match result:
    case Success(payload=payload):
        ...  # TODO: Handle 'payload' of type A2ADemoOut
    case Failure(error=error):
        ...  # TODO: Handle 'error' of type ApiA2ADemoErrorBody
```

**Async**

```python
result = await async_client.agent.with_raw_response.api_a2a_demo()
match result:
    case Success(payload=payload):
        ...  # TODO: Handle 'payload' of type A2ADemoOut
    case Failure(error=error):
        ...  # TODO: Handle 'error' of type ApiA2ADemoErrorBody
```

</dd>
</dl>

### Parameters

<dl>
<dd>

| Name | Type | Description |
| --- | --- | --- |
| <code>request_options</code> | <code>[RequestOptionsOrDict](helm_api/core/request_options.py) \| None</code> | Per-call overrides for this one request, such as a timeout, extra headers, or its retry count and statuses. |

</dd>
</dl>

### Response

<dl>
<dd>

**Returns**: <code>[ApiResult](helm_api/core/results.py)&#91;[A2ADemoOut](helm_api/models/a2_a_demo_out.py), [ApiA2ADemoErrorBody](helm_api/errors/api_a2_a_demo_error.py)&#93;</code>

**On `Success`**: `payload` is <code>[A2ADemoOut](helm_api/models/a2_a_demo_out.py)</code> -- Successful Response

**On `Failure`**: `error` is <code>[ApiA2ADemoErrorBody](helm_api/errors/api_a2_a_demo_error.py)</code>

Mapped in first-match order -- an earlier row wins over a later range that also covers the status:

| Status | `error` is |
| --- | --- |
| 400 | <code>[ErrorOut](helm_api/models/error_out.py)</code> |
| anything unmapped | <code>[RawError](helm_api/core/results.py)</code> |

</dd>
</dl>

</dd>
</dl>

</details>

## Ai

> Source: [Ai](helm_api/apis/ai.py)

<details>
<summary><code>def api_policy(body: PolicyIn | PolicyInDict, *, request_options: RequestOptionsOrDict | None = None) -> ApiResult[PolicyOut, ApiPolicyErrorBody]</code></summary>

<dl>
<dd>

### Description

<dl>
<dd>

Compile an English treasury policy into objective weights and hard constraints with the live model.

</dd>
</dl>

### Usage

<dl>
<dd>

**Sync**

```python
result = client.ai.with_raw_response.api_policy(PolicyIn())
match result:
    case Success(payload=payload):
        ...  # TODO: Handle 'payload' of type PolicyOut
    case Failure(error=error):
        ...  # TODO: Handle 'error' of type ApiPolicyErrorBody
```

**Async**

```python
result = await async_client.ai.with_raw_response.api_policy(PolicyIn())
match result:
    case Success(payload=payload):
        ...  # TODO: Handle 'payload' of type PolicyOut
    case Failure(error=error):
        ...  # TODO: Handle 'error' of type ApiPolicyErrorBody
```

</dd>
</dl>

### Parameters

<dl>
<dd>

| Name | Type | Description |
| --- | --- | --- |
| <code>body</code> | <code>[PolicyIn](helm_api/models/policy_in.py) \| [PolicyInDict](helm_api/models/policy_in.py)</code> | The request body. |
| <code>request_options</code> | <code>[RequestOptionsOrDict](helm_api/core/request_options.py) \| None</code> | Per-call overrides for this one request, such as a timeout, extra headers, or its retry count and statuses. |

</dd>
</dl>

### Response

<dl>
<dd>

**Returns**: <code>[ApiResult](helm_api/core/results.py)&#91;[PolicyOut](helm_api/models/policy_out.py), [ApiPolicyErrorBody](helm_api/errors/api_policy_error.py)&#93;</code>

**On `Success`**: `payload` is <code>[PolicyOut](helm_api/models/policy_out.py)</code> -- Successful Response

**On `Failure`**: `error` is <code>[ApiPolicyErrorBody](helm_api/errors/api_policy_error.py)</code>

Mapped in first-match order -- an earlier row wins over a later range that also covers the status:

| Status | `error` is |
| --- | --- |
| 400 | <code>[ErrorOut](helm_api/models/error_out.py)</code> |
| 422 | <code>[HttpValidationError](helm_api/models/http_validation_error.py)</code> |
| anything unmapped | <code>[RawError](helm_api/core/results.py)</code> |

</dd>
</dl>

</dd>
</dl>

</details>

<details>
<summary><code>def api_signal(body: SignalIn | SignalInDict, *, request_options: RequestOptionsOrDict | None = None) -> ApiResult[SignalOut, ApiSignalErrorBody]</code></summary>

<dl>
<dd>

### Description

<dl>
<dd>

Read an operational signal into a bounded, per-period forecast adjustment (live model).

</dd>
</dl>

### Usage

<dl>
<dd>

**Sync**

```python
result = client.ai.with_raw_response.api_signal(SignalIn())
match result:
    case Success(payload=payload):
        ...  # TODO: Handle 'payload' of type SignalOut
    case Failure(error=error):
        ...  # TODO: Handle 'error' of type ApiSignalErrorBody
```

**Async**

```python
result = await async_client.ai.with_raw_response.api_signal(SignalIn())
match result:
    case Success(payload=payload):
        ...  # TODO: Handle 'payload' of type SignalOut
    case Failure(error=error):
        ...  # TODO: Handle 'error' of type ApiSignalErrorBody
```

</dd>
</dl>

### Parameters

<dl>
<dd>

| Name | Type | Description |
| --- | --- | --- |
| <code>body</code> | <code>[SignalIn](helm_api/models/signal_in.py) \| [SignalInDict](helm_api/models/signal_in.py)</code> | The request body. |
| <code>request_options</code> | <code>[RequestOptionsOrDict](helm_api/core/request_options.py) \| None</code> | Per-call overrides for this one request, such as a timeout, extra headers, or its retry count and statuses. |

</dd>
</dl>

### Response

<dl>
<dd>

**Returns**: <code>[ApiResult](helm_api/core/results.py)&#91;[SignalOut](helm_api/models/signal_out.py), [ApiSignalErrorBody](helm_api/errors/api_signal_error.py)&#93;</code>

**On `Success`**: `payload` is <code>[SignalOut](helm_api/models/signal_out.py)</code> -- Successful Response

**On `Failure`**: `error` is <code>[ApiSignalErrorBody](helm_api/errors/api_signal_error.py)</code>

Mapped in first-match order -- an earlier row wins over a later range that also covers the status:

| Status | `error` is |
| --- | --- |
| 400 | <code>[ErrorOut](helm_api/models/error_out.py)</code> |
| 422 | <code>[HttpValidationError](helm_api/models/http_validation_error.py)</code> |
| anything unmapped | <code>[RawError](helm_api/core/results.py)</code> |

</dd>
</dl>

</dd>
</dl>

</details>

## Commerce

> Source: [Commerce](helm_api/apis/commerce.py)

<details>
<summary><code>def api_escrow_demo(body: EscrowIn | EscrowInDict, *, request_options: RequestOptionsOrDict | None = None) -> ApiResult[EscrowOut, ApiEscrowDemoErrorBody]</code></summary>

<dl>
<dd>

### Description

<dl>
<dd>

Pay-on-proof escrow: PayPal authorizes and holds the money, deterministic criteria decide
release (capture) or refund (void). A cheat flag sends a junk delivery to show the money is
returned, not released.

</dd>
</dl>

### Usage

<dl>
<dd>

**Sync**

```python
result = client.commerce.with_raw_response.api_escrow_demo(EscrowIn())
match result:
    case Success(payload=payload):
        ...  # TODO: Handle 'payload' of type EscrowOut
    case Failure(error=error):
        ...  # TODO: Handle 'error' of type ApiEscrowDemoErrorBody
```

**Async**

```python
result = await async_client.commerce.with_raw_response.api_escrow_demo(EscrowIn())
match result:
    case Success(payload=payload):
        ...  # TODO: Handle 'payload' of type EscrowOut
    case Failure(error=error):
        ...  # TODO: Handle 'error' of type ApiEscrowDemoErrorBody
```

</dd>
</dl>

### Parameters

<dl>
<dd>

| Name | Type | Description |
| --- | --- | --- |
| <code>body</code> | <code>[EscrowIn](helm_api/models/escrow_in.py) \| [EscrowInDict](helm_api/models/escrow_in.py)</code> | The request body. |
| <code>request_options</code> | <code>[RequestOptionsOrDict](helm_api/core/request_options.py) \| None</code> | Per-call overrides for this one request, such as a timeout, extra headers, or its retry count and statuses. |

</dd>
</dl>

### Response

<dl>
<dd>

**Returns**: <code>[ApiResult](helm_api/core/results.py)&#91;[EscrowOut](helm_api/models/escrow_out.py), [ApiEscrowDemoErrorBody](helm_api/errors/api_escrow_demo_error.py)&#93;</code>

**On `Success`**: `payload` is <code>[EscrowOut](helm_api/models/escrow_out.py)</code> -- Successful Response

**On `Failure`**: `error` is <code>[ApiEscrowDemoErrorBody](helm_api/errors/api_escrow_demo_error.py)</code>

Mapped in first-match order -- an earlier row wins over a later range that also covers the status:

| Status | `error` is |
| --- | --- |
| 400 | <code>[ErrorOut](helm_api/models/error_out.py)</code> |
| 422 | <code>[HttpValidationError](helm_api/models/http_validation_error.py)</code> |
| anything unmapped | <code>[RawError](helm_api/core/results.py)</code> |

</dd>
</dl>

</dd>
</dl>

</details>

<details>
<summary><code>def api_shop_buy(body: ShopBuyIn | ShopBuyInDict, *, request_options: RequestOptionsOrDict | None = None) -> ApiResult[ShopBuyOut, ApiShopBuyErrorBody]</code></summary>

<dl>
<dd>

### Description

<dl>
<dd>

Buy a found product: the person's owner-signed spend mandate authorizes the purchase
(budget and per-item cap enforced by the signature, not a rule), and pay-on-proof escrow
settles it on PayPal. The same account that earns can spend.

</dd>
</dl>

### Usage

<dl>
<dd>

**Sync**

```python
result = client.commerce.with_raw_response.api_shop_buy(ShopBuyIn())
match result:
    case Success(payload=payload):
        ...  # TODO: Handle 'payload' of type ShopBuyOut
    case Failure(error=error):
        ...  # TODO: Handle 'error' of type ApiShopBuyErrorBody
```

**Async**

```python
result = await async_client.commerce.with_raw_response.api_shop_buy(ShopBuyIn())
match result:
    case Success(payload=payload):
        ...  # TODO: Handle 'payload' of type ShopBuyOut
    case Failure(error=error):
        ...  # TODO: Handle 'error' of type ApiShopBuyErrorBody
```

</dd>
</dl>

### Parameters

<dl>
<dd>

| Name | Type | Description |
| --- | --- | --- |
| <code>body</code> | <code>[ShopBuyIn](helm_api/models/shop_buy_in.py) \| [ShopBuyInDict](helm_api/models/shop_buy_in.py)</code> | The request body. |
| <code>request_options</code> | <code>[RequestOptionsOrDict](helm_api/core/request_options.py) \| None</code> | Per-call overrides for this one request, such as a timeout, extra headers, or its retry count and statuses. |

</dd>
</dl>

### Response

<dl>
<dd>

**Returns**: <code>[ApiResult](helm_api/core/results.py)&#91;[ShopBuyOut](helm_api/models/shop_buy_out.py), [ApiShopBuyErrorBody](helm_api/errors/api_shop_buy_error.py)&#93;</code>

**On `Success`**: `payload` is <code>[ShopBuyOut](helm_api/models/shop_buy_out.py)</code> -- Successful Response

**On `Failure`**: `error` is <code>[ApiShopBuyErrorBody](helm_api/errors/api_shop_buy_error.py)</code>

Mapped in first-match order -- an earlier row wins over a later range that also covers the status:

| Status | `error` is |
| --- | --- |
| 400 | <code>[ErrorOut](helm_api/models/error_out.py)</code> |
| 422 | <code>[HttpValidationError](helm_api/models/http_validation_error.py)</code> |
| anything unmapped | <code>[RawError](helm_api/core/results.py)</code> |

</dd>
</dl>

</dd>
</dl>

</details>

<details>
<summary><code>def api_shop_search(body: ShopSearchIn | ShopSearchInDict, *, request_options: RequestOptionsOrDict | None = None) -> ApiResult[ShopSearchOut, ApiShopSearchErrorBody]</code></summary>

<dl>
<dd>

### Description

<dl>
<dd>

The buyer side: a person spends earnings on a real product. Finds products with Channel3
when a key is set, or a demo catalog otherwise, and flags which fit the stated budget.

</dd>
</dl>

### Usage

<dl>
<dd>

**Sync**

```python
result = client.commerce.with_raw_response.api_shop_search(ShopSearchIn())
match result:
    case Success(payload=payload):
        ...  # TODO: Handle 'payload' of type ShopSearchOut
    case Failure(error=error):
        ...  # TODO: Handle 'error' of type ApiShopSearchErrorBody
```

**Async**

```python
result = await async_client.commerce.with_raw_response.api_shop_search(ShopSearchIn())
match result:
    case Success(payload=payload):
        ...  # TODO: Handle 'payload' of type ShopSearchOut
    case Failure(error=error):
        ...  # TODO: Handle 'error' of type ApiShopSearchErrorBody
```

</dd>
</dl>

### Parameters

<dl>
<dd>

| Name | Type | Description |
| --- | --- | --- |
| <code>body</code> | <code>[ShopSearchIn](helm_api/models/shop_search_in.py) \| [ShopSearchInDict](helm_api/models/shop_search_in.py)</code> | The request body. |
| <code>request_options</code> | <code>[RequestOptionsOrDict](helm_api/core/request_options.py) \| None</code> | Per-call overrides for this one request, such as a timeout, extra headers, or its retry count and statuses. |

</dd>
</dl>

### Response

<dl>
<dd>

**Returns**: <code>[ApiResult](helm_api/core/results.py)&#91;[ShopSearchOut](helm_api/models/shop_search_out.py), [ApiShopSearchErrorBody](helm_api/errors/api_shop_search_error.py)&#93;</code>

**On `Success`**: `payload` is <code>[ShopSearchOut](helm_api/models/shop_search_out.py)</code> -- Successful Response

**On `Failure`**: `error` is <code>[ApiShopSearchErrorBody](helm_api/errors/api_shop_search_error.py)</code>

Mapped in first-match order -- an earlier row wins over a later range that also covers the status:

| Status | `error` is |
| --- | --- |
| 400 | <code>[ErrorOut](helm_api/models/error_out.py)</code> |
| 422 | <code>[HttpValidationError](helm_api/models/http_validation_error.py)</code> |
| anything unmapped | <code>[RawError](helm_api/core/results.py)</code> |

</dd>
</dl>

</dd>
</dl>

</details>

## Dashboard

> Source: [Dashboard](helm_api/apis/dashboard.py)

<details>
<summary><code>def data(*, request_options: RequestOptionsOrDict | None = None) -> ApiResult[Any, RawError]</code></summary>

<dl>
<dd>

### Description

<dl>
<dd>

The complete cached dashboard payload (headline, scenarios, directory, reinvest, engine).

</dd>
</dl>

### Usage

<dl>
<dd>

**Sync**

```python
result = client.dashboard.with_raw_response.data()
match result:
    case Success(payload=payload):
        ...  # TODO: Handle 'payload' of type Any
    case Failure(error=error):
        ...  # TODO: Handle 'error' of type RawError
```

**Async**

```python
result = await async_client.dashboard.with_raw_response.data()
match result:
    case Success(payload=payload):
        ...  # TODO: Handle 'payload' of type Any
    case Failure(error=error):
        ...  # TODO: Handle 'error' of type RawError
```

</dd>
</dl>

### Parameters

<dl>
<dd>

| Name | Type | Description |
| --- | --- | --- |
| <code>request_options</code> | <code>[RequestOptionsOrDict](helm_api/core/request_options.py) \| None</code> | Per-call overrides for this one request, such as a timeout, extra headers, or its retry count and statuses. |

</dd>
</dl>

### Response

<dl>
<dd>

**Returns**: <code>[ApiResult](helm_api/core/results.py)&#91;Any, [RawError](helm_api/core/results.py)&#93;</code>

**On `Success`**: `payload` is <code>Any</code> -- Successful Response

**On `Failure`**: `error` is <code>[RawError](helm_api/core/results.py)</code>

</dd>
</dl>

</dd>
</dl>

</details>

<details>
<summary><code>def healthz(*, request_options: RequestOptionsOrDict | None = None) -> ApiResult[str, RawError]</code></summary>

<dl>
<dd>

### Description

<dl>
<dd>

Returns 'ok' when the server is up.

</dd>
</dl>

### Usage

<dl>
<dd>

**Sync**

```python
result = client.dashboard.with_raw_response.healthz()
match result:
    case Success(payload=payload):
        ...  # TODO: Handle 'payload' of type str
    case Failure(error=error):
        ...  # TODO: Handle 'error' of type RawError
```

**Async**

```python
result = await async_client.dashboard.with_raw_response.healthz()
match result:
    case Success(payload=payload):
        ...  # TODO: Handle 'payload' of type str
    case Failure(error=error):
        ...  # TODO: Handle 'error' of type RawError
```

</dd>
</dl>

### Parameters

<dl>
<dd>

| Name | Type | Description |
| --- | --- | --- |
| <code>request_options</code> | <code>[RequestOptionsOrDict](helm_api/core/request_options.py) \| None</code> | Per-call overrides for this one request, such as a timeout, extra headers, or its retry count and statuses. |

</dd>
</dl>

### Response

<dl>
<dd>

**Returns**: <code>[ApiResult](helm_api/core/results.py)&#91;str, [RawError](helm_api/core/results.py)&#93;</code>

**On `Success`**: `payload` is <code>str</code> -- Successful Response

**On `Failure`**: `error` is <code>[RawError](helm_api/core/results.py)</code>

</dd>
</dl>

</dd>
</dl>

</details>

<details>
<summary><code>def index(*, request_options: RequestOptionsOrDict | None = None) -> ApiResult[None, RawError]</code></summary>

<dl>
<dd>

### Description

<dl>
<dd>

Serve the single-page dashboard with its data embedded.

</dd>
</dl>

### Usage

<dl>
<dd>

**Sync**

```python
result = client.dashboard.with_raw_response.index()
match result:
    case Success():
        ...  # 2xx, no content
    case Failure(error=error):
        ...  # TODO: Handle 'error' of type RawError
```

**Async**

```python
result = await async_client.dashboard.with_raw_response.index()
match result:
    case Success():
        ...  # 2xx, no content
    case Failure(error=error):
        ...  # TODO: Handle 'error' of type RawError
```

</dd>
</dl>

### Parameters

<dl>
<dd>

| Name | Type | Description |
| --- | --- | --- |
| <code>request_options</code> | <code>[RequestOptionsOrDict](helm_api/core/request_options.py) \| None</code> | Per-call overrides for this one request, such as a timeout, extra headers, or its retry count and statuses. |

</dd>
</dl>

### Response

<dl>
<dd>

**Returns**: <code>[ApiResult](helm_api/core/results.py)&#91;None, [RawError](helm_api/core/results.py)&#93;</code>

**On `Success`**: the 2xx carries no content; `payload` is <code>None</code>

**On `Failure`**: `error` is <code>[RawError](helm_api/core/results.py)</code>

</dd>
</dl>

</dd>
</dl>

</details>

## Pooling

> Source: [Pooling](helm_api/apis/pooling.py)

<details>
<summary><code>def api_pool_groupbuy(body: GroupBuyIn | GroupBuyInDict, *, request_options: RequestOptionsOrDict | None = None) -> ApiResult[GroupBuyOut, ApiPoolGroupbuyErrorBody]</code></summary>

<dl>
<dd>

### Description

<dl>
<dd>

Several people buy the same item together to clear a volume-discount tier none could reach
alone. Each contribution is signed; the discounted total is shared pro-rata and the saving is
attributed by the Shapley value.

</dd>
</dl>

### Usage

<dl>
<dd>

**Sync**

```python
result = client.pooling.with_raw_response.api_pool_groupbuy(GroupBuyIn())
match result:
    case Success(payload=payload):
        ...  # TODO: Handle 'payload' of type GroupBuyOut
    case Failure(error=error):
        ...  # TODO: Handle 'error' of type ApiPoolGroupbuyErrorBody
```

**Async**

```python
result = await async_client.pooling.with_raw_response.api_pool_groupbuy(GroupBuyIn())
match result:
    case Success(payload=payload):
        ...  # TODO: Handle 'payload' of type GroupBuyOut
    case Failure(error=error):
        ...  # TODO: Handle 'error' of type ApiPoolGroupbuyErrorBody
```

</dd>
</dl>

### Parameters

<dl>
<dd>

| Name | Type | Description |
| --- | --- | --- |
| <code>body</code> | <code>[GroupBuyIn](helm_api/models/group_buy_in.py) \| [GroupBuyInDict](helm_api/models/group_buy_in.py)</code> | The request body. |
| <code>request_options</code> | <code>[RequestOptionsOrDict](helm_api/core/request_options.py) \| None</code> | Per-call overrides for this one request, such as a timeout, extra headers, or its retry count and statuses. |

</dd>
</dl>

### Response

<dl>
<dd>

**Returns**: <code>[ApiResult](helm_api/core/results.py)&#91;[GroupBuyOut](helm_api/models/group_buy_out.py), [ApiPoolGroupbuyErrorBody](helm_api/errors/api_pool_groupbuy_error.py)&#93;</code>

**On `Success`**: `payload` is <code>[GroupBuyOut](helm_api/models/group_buy_out.py)</code> -- Successful Response

**On `Failure`**: `error` is <code>[ApiPoolGroupbuyErrorBody](helm_api/errors/api_pool_groupbuy_error.py)</code>

Mapped in first-match order -- an earlier row wins over a later range that also covers the status:

| Status | `error` is |
| --- | --- |
| 400 | <code>[ErrorOut](helm_api/models/error_out.py)</code> |
| 422 | <code>[HttpValidationError](helm_api/models/http_validation_error.py)</code> |
| anything unmapped | <code>[RawError](helm_api/core/results.py)</code> |

</dd>
</dl>

</dd>
</dl>

</details>

<details>
<summary><code>def api_pool_invest(body: PoolInvestIn | PoolInvestInDict, *, request_options: RequestOptionsOrDict | None = None) -> ApiResult[PoolInvestOut, ApiPoolInvestErrorBody]</code></summary>

<dl>
<dd>

### Description

<dl>
<dd>

Several people pool cash to co-own one position. The server signs each member's
contribution with their own ES256 mandate, optionally forging one to show it is excluded,
then places ONE real paper order for the pooled total and splits the units pro-rata.

</dd>
</dl>

### Usage

<dl>
<dd>

**Sync**

```python
result = client.pooling.with_raw_response.api_pool_invest(PoolInvestIn())
match result:
    case Success(payload=payload):
        ...  # TODO: Handle 'payload' of type PoolInvestOut
    case Failure(error=error):
        ...  # TODO: Handle 'error' of type ApiPoolInvestErrorBody
```

**Async**

```python
result = await async_client.pooling.with_raw_response.api_pool_invest(PoolInvestIn())
match result:
    case Success(payload=payload):
        ...  # TODO: Handle 'payload' of type PoolInvestOut
    case Failure(error=error):
        ...  # TODO: Handle 'error' of type ApiPoolInvestErrorBody
```

</dd>
</dl>

### Parameters

<dl>
<dd>

| Name | Type | Description |
| --- | --- | --- |
| <code>body</code> | <code>[PoolInvestIn](helm_api/models/pool_invest_in.py) \| [PoolInvestInDict](helm_api/models/pool_invest_in.py)</code> | The request body. |
| <code>request_options</code> | <code>[RequestOptionsOrDict](helm_api/core/request_options.py) \| None</code> | Per-call overrides for this one request, such as a timeout, extra headers, or its retry count and statuses. |

</dd>
</dl>

### Response

<dl>
<dd>

**Returns**: <code>[ApiResult](helm_api/core/results.py)&#91;[PoolInvestOut](helm_api/models/pool_invest_out.py), [ApiPoolInvestErrorBody](helm_api/errors/api_pool_invest_error.py)&#93;</code>

**On `Success`**: `payload` is <code>[PoolInvestOut](helm_api/models/pool_invest_out.py)</code> -- Successful Response

**On `Failure`**: `error` is <code>[ApiPoolInvestErrorBody](helm_api/errors/api_pool_invest_error.py)</code>

Mapped in first-match order -- an earlier row wins over a later range that also covers the status:

| Status | `error` is |
| --- | --- |
| 400 | <code>[ErrorOut](helm_api/models/error_out.py)</code> |
| 422 | <code>[HttpValidationError](helm_api/models/http_validation_error.py)</code> |
| anything unmapped | <code>[RawError](helm_api/core/results.py)</code> |

</dd>
</dl>

</dd>
</dl>

</details>

## Proofs

> Source: [Proofs](helm_api/apis/proofs.py)

<details>
<summary><code>def api_reserves_prove(body: ReservesIn | ReservesInDict, *, request_options: RequestOptionsOrDict | None = None) -> ApiResult[ReservesOut, ApiReservesProveErrorBody]</code></summary>

<dl>
<dd>

### Description

<dl>
<dd>

Prove in zero knowledge that the safety fund covers its liabilities without revealing any
balance. Returns only the verification outcome and the proof shape; the amounts never leave
the server.

</dd>
</dl>

### Usage

<dl>
<dd>

**Sync**

```python
result = client.proofs.with_raw_response.api_reserves_prove(ReservesIn())
match result:
    case Success(payload=payload):
        ...  # TODO: Handle 'payload' of type ReservesOut
    case Failure(error=error):
        ...  # TODO: Handle 'error' of type ApiReservesProveErrorBody
```

**Async**

```python
result = await async_client.proofs.with_raw_response.api_reserves_prove(ReservesIn())
match result:
    case Success(payload=payload):
        ...  # TODO: Handle 'payload' of type ReservesOut
    case Failure(error=error):
        ...  # TODO: Handle 'error' of type ApiReservesProveErrorBody
```

</dd>
</dl>

### Parameters

<dl>
<dd>

| Name | Type | Description |
| --- | --- | --- |
| <code>body</code> | <code>[ReservesIn](helm_api/models/reserves_in.py) \| [ReservesInDict](helm_api/models/reserves_in.py)</code> | The request body. |
| <code>request_options</code> | <code>[RequestOptionsOrDict](helm_api/core/request_options.py) \| None</code> | Per-call overrides for this one request, such as a timeout, extra headers, or its retry count and statuses. |

</dd>
</dl>

### Response

<dl>
<dd>

**Returns**: <code>[ApiResult](helm_api/core/results.py)&#91;[ReservesOut](helm_api/models/reserves_out.py), [ApiReservesProveErrorBody](helm_api/errors/api_reserves_prove_error.py)&#93;</code>

**On `Success`**: `payload` is <code>[ReservesOut](helm_api/models/reserves_out.py)</code> -- Successful Response

**On `Failure`**: `error` is <code>[ApiReservesProveErrorBody](helm_api/errors/api_reserves_prove_error.py)</code>

Mapped in first-match order -- an earlier row wins over a later range that also covers the status:

| Status | `error` is |
| --- | --- |
| 400 | <code>[ErrorOut](helm_api/models/error_out.py)</code> |
| 422 | <code>[HttpValidationError](helm_api/models/http_validation_error.py)</code> |
| anything unmapped | <code>[RawError](helm_api/core/results.py)</code> |

</dd>
</dl>

</dd>
</dl>

</details>

<details>
<summary><code>def api_verify_mandate(body: VerifyMandateIn | VerifyMandateInDict, *, request_options: RequestOptionsOrDict | None = None) -> ApiResult[VerifyMandateOut, ApiVerifyMandateErrorBody]</code></summary>

<dl>
<dd>

### Description

<dl>
<dd>

Prove with Z3 that an agent's signed mandate is budget-bounded for ANY sequence of deals
(an unbounded inductive-invariant proof), show the guard set is necessary via a counterexample,
and return an ES256-signed authorization verdict. A forge flag tampers the mandate to show it
is rejected.

</dd>
</dl>

### Usage

<dl>
<dd>

**Sync**

```python
result = client.proofs.with_raw_response.api_verify_mandate(VerifyMandateIn())
match result:
    case Success(payload=payload):
        ...  # TODO: Handle 'payload' of type VerifyMandateOut
    case Failure(error=error):
        ...  # TODO: Handle 'error' of type ApiVerifyMandateErrorBody
```

**Async**

```python
result = await async_client.proofs.with_raw_response.api_verify_mandate(VerifyMandateIn())
match result:
    case Success(payload=payload):
        ...  # TODO: Handle 'payload' of type VerifyMandateOut
    case Failure(error=error):
        ...  # TODO: Handle 'error' of type ApiVerifyMandateErrorBody
```

</dd>
</dl>

### Parameters

<dl>
<dd>

| Name | Type | Description |
| --- | --- | --- |
| <code>body</code> | <code>[VerifyMandateIn](helm_api/models/verify_mandate_in.py) \| [VerifyMandateInDict](helm_api/models/verify_mandate_in.py)</code> | The request body. |
| <code>request_options</code> | <code>[RequestOptionsOrDict](helm_api/core/request_options.py) \| None</code> | Per-call overrides for this one request, such as a timeout, extra headers, or its retry count and statuses. |

</dd>
</dl>

### Response

<dl>
<dd>

**Returns**: <code>[ApiResult](helm_api/core/results.py)&#91;[VerifyMandateOut](helm_api/models/verify_mandate_out.py), [ApiVerifyMandateErrorBody](helm_api/errors/api_verify_mandate_error.py)&#93;</code>

**On `Success`**: `payload` is <code>[VerifyMandateOut](helm_api/models/verify_mandate_out.py)</code> -- Successful Response

**On `Failure`**: `error` is <code>[ApiVerifyMandateErrorBody](helm_api/errors/api_verify_mandate_error.py)</code>

Mapped in first-match order -- an earlier row wins over a later range that also covers the status:

| Status | `error` is |
| --- | --- |
| 400 | <code>[ErrorOut](helm_api/models/error_out.py)</code> |
| 422 | <code>[HttpValidationError](helm_api/models/http_validation_error.py)</code> |
| anything unmapped | <code>[RawError](helm_api/core/results.py)</code> |

</dd>
</dl>

</dd>
</dl>

</details>

## Treasury

> Source: [Treasury](helm_api/apis/treasury.py)

<details>
<summary><code>def api_advance(body: AdvanceIn | AdvanceInDict, *, request_options: RequestOptionsOrDict | None = None) -> ApiResult[AdvanceOut, ApiAdvanceErrorBody]</code></summary>

<dl>
<dd>

### Description

<dl>
<dd>

A safety-capped, risk-priced advance offer against proven earnings.

</dd>
</dl>

### Usage

<dl>
<dd>

**Sync**

```python
result = client.treasury.with_raw_response.api_advance(AdvanceIn())
match result:
    case Success(payload=payload):
        ...  # TODO: Handle 'payload' of type AdvanceOut
    case Failure(error=error):
        ...  # TODO: Handle 'error' of type ApiAdvanceErrorBody
```

**Async**

```python
result = await async_client.treasury.with_raw_response.api_advance(AdvanceIn())
match result:
    case Success(payload=payload):
        ...  # TODO: Handle 'payload' of type AdvanceOut
    case Failure(error=error):
        ...  # TODO: Handle 'error' of type ApiAdvanceErrorBody
```

</dd>
</dl>

### Parameters

<dl>
<dd>

| Name | Type | Description |
| --- | --- | --- |
| <code>body</code> | <code>[AdvanceIn](helm_api/models/advance_in.py) \| [AdvanceInDict](helm_api/models/advance_in.py)</code> | The request body. |
| <code>request_options</code> | <code>[RequestOptionsOrDict](helm_api/core/request_options.py) \| None</code> | Per-call overrides for this one request, such as a timeout, extra headers, or its retry count and statuses. |

</dd>
</dl>

### Response

<dl>
<dd>

**Returns**: <code>[ApiResult](helm_api/core/results.py)&#91;[AdvanceOut](helm_api/models/advance_out.py), [ApiAdvanceErrorBody](helm_api/errors/api_advance_error.py)&#93;</code>

**On `Success`**: `payload` is <code>[AdvanceOut](helm_api/models/advance_out.py)</code> -- Successful Response

**On `Failure`**: `error` is <code>[ApiAdvanceErrorBody](helm_api/errors/api_advance_error.py)</code>

Mapped in first-match order -- an earlier row wins over a later range that also covers the status:

| Status | `error` is |
| --- | --- |
| 400 | <code>[ErrorOut](helm_api/models/error_out.py)</code> |
| 422 | <code>[HttpValidationError](helm_api/models/http_validation_error.py)</code> |
| anything unmapped | <code>[RawError](helm_api/core/results.py)</code> |

</dd>
</dl>

</dd>
</dl>

</details>

<details>
<summary><code>def api_invest(body: InvestIn | InvestInDict, *, request_options: RequestOptionsOrDict | None = None) -> ApiResult[InvestOut, ApiInvestErrorBody]</code></summary>

<dl>
<dd>

### Description

<dl>
<dd>

Invest a notional amount across the basket at live prices.

</dd>
</dl>

### Usage

<dl>
<dd>

**Sync**

```python
result = client.treasury.with_raw_response.api_invest(InvestIn())
match result:
    case Success(payload=payload):
        ...  # TODO: Handle 'payload' of type InvestOut
    case Failure(error=error):
        ...  # TODO: Handle 'error' of type ApiInvestErrorBody
```

**Async**

```python
result = await async_client.treasury.with_raw_response.api_invest(InvestIn())
match result:
    case Success(payload=payload):
        ...  # TODO: Handle 'payload' of type InvestOut
    case Failure(error=error):
        ...  # TODO: Handle 'error' of type ApiInvestErrorBody
```

</dd>
</dl>

### Parameters

<dl>
<dd>

| Name | Type | Description |
| --- | --- | --- |
| <code>body</code> | <code>[InvestIn](helm_api/models/invest_in.py) \| [InvestInDict](helm_api/models/invest_in.py)</code> | The request body. |
| <code>request_options</code> | <code>[RequestOptionsOrDict](helm_api/core/request_options.py) \| None</code> | Per-call overrides for this one request, such as a timeout, extra headers, or its retry count and statuses. |

</dd>
</dl>

### Response

<dl>
<dd>

**Returns**: <code>[ApiResult](helm_api/core/results.py)&#91;[InvestOut](helm_api/models/invest_out.py), [ApiInvestErrorBody](helm_api/errors/api_invest_error.py)&#93;</code>

**On `Success`**: `payload` is <code>[InvestOut](helm_api/models/invest_out.py)</code> -- Successful Response

**On `Failure`**: `error` is <code>[ApiInvestErrorBody](helm_api/errors/api_invest_error.py)</code>

Mapped in first-match order -- an earlier row wins over a later range that also covers the status:

| Status | `error` is |
| --- | --- |
| 400 | <code>[ErrorOut](helm_api/models/error_out.py)</code> |
| 422 | <code>[HttpValidationError](helm_api/models/http_validation_error.py)</code> |
| anything unmapped | <code>[RawError](helm_api/core/results.py)</code> |

</dd>
</dl>

</dd>
</dl>

</details>

<details>
<summary><code>def api_quote(*, ticker: str | None = "SPY", request_options: RequestOptionsOrDict | None = None) -> ApiResult[QuoteOut, ApiQuoteErrorBody]</code></summary>

<dl>
<dd>

### Description

<dl>
<dd>

Latest real market price for a ticker (Alpaca paper when keys are present, else a live-price source).

</dd>
</dl>

### Usage

<dl>
<dd>

**Sync**

```python
result = client.treasury.with_raw_response.api_quote(ticker="SPY")
match result:
    case Success(payload=payload):
        ...  # TODO: Handle 'payload' of type QuoteOut
    case Failure(error=error):
        ...  # TODO: Handle 'error' of type ApiQuoteErrorBody
```

**Async**

```python
result = await async_client.treasury.with_raw_response.api_quote(ticker="SPY")
match result:
    case Success(payload=payload):
        ...  # TODO: Handle 'payload' of type QuoteOut
    case Failure(error=error):
        ...  # TODO: Handle 'error' of type ApiQuoteErrorBody
```

</dd>
</dl>

### Parameters

<dl>
<dd>

| Name | Type | Description |
| --- | --- | --- |
| <code>ticker</code> | <code>str \| None</code> | Ticker symbol to quote.<br>**Default**: <code>"SPY"</code> |
| <code>request_options</code> | <code>[RequestOptionsOrDict](helm_api/core/request_options.py) \| None</code> | Per-call overrides for this one request, such as a timeout, extra headers, or its retry count and statuses. |

</dd>
</dl>

### Response

<dl>
<dd>

**Returns**: <code>[ApiResult](helm_api/core/results.py)&#91;[QuoteOut](helm_api/models/quote_out.py), [ApiQuoteErrorBody](helm_api/errors/api_quote_error.py)&#93;</code>

**On `Success`**: `payload` is <code>[QuoteOut](helm_api/models/quote_out.py)</code> -- Successful Response

**On `Failure`**: `error` is <code>[ApiQuoteErrorBody](helm_api/errors/api_quote_error.py)</code>

Mapped in first-match order -- an earlier row wins over a later range that also covers the status:

| Status | `error` is |
| --- | --- |
| 400 | <code>[ErrorOut](helm_api/models/error_out.py)</code> |
| 422 | <code>[HttpValidationError](helm_api/models/http_validation_error.py)</code> |
| anything unmapped | <code>[RawError](helm_api/core/results.py)</code> |

</dd>
</dl>

</dd>
</dl>

</details>

<details>
<summary><code>def api_tax(*, country: str | None = "US", gross: float | None = 0.0, transactions: int | None = 0, fees: float | None = 0.0, request_options: RequestOptionsOrDict | None = None) -> ApiResult[TaxOut, ApiTaxErrorBody]</code></summary>

<dl>
<dd>

### Description

<dl>
<dd>

A creator's reporting regime (US 1099-K thresholds or EU DAC7).

</dd>
</dl>

### Usage

<dl>
<dd>

**Sync**

```python
result = client.treasury.with_raw_response.api_tax(country="US", gross=25000, transactions=250, fees=0)
match result:
    case Success(payload=payload):
        ...  # TODO: Handle 'payload' of type TaxOut
    case Failure(error=error):
        ...  # TODO: Handle 'error' of type ApiTaxErrorBody
```

**Async**

```python
result = await async_client.treasury.with_raw_response.api_tax(country="US", gross=25000, transactions=250, fees=0)
match result:
    case Success(payload=payload):
        ...  # TODO: Handle 'payload' of type TaxOut
    case Failure(error=error):
        ...  # TODO: Handle 'error' of type ApiTaxErrorBody
```

</dd>
</dl>

### Parameters

<dl>
<dd>

| Name | Type | Description |
| --- | --- | --- |
| <code>country</code> | <code>str \| None</code> | Two-letter country code.<br>**Default**: <code>"US"</code> |
| <code>gross</code> | <code>float \| None</code> | Gross for the year.<br>**Default**: <code>0.0</code> |
| <code>transactions</code> | <code>int \| None</code> | Transaction count.<br>**Default**: <code>0</code> |
| <code>fees</code> | <code>float \| None</code> | Platform fees withheld.<br>**Default**: <code>0.0</code> |
| <code>request_options</code> | <code>[RequestOptionsOrDict](helm_api/core/request_options.py) \| None</code> | Per-call overrides for this one request, such as a timeout, extra headers, or its retry count and statuses. |

</dd>
</dl>

### Response

<dl>
<dd>

**Returns**: <code>[ApiResult](helm_api/core/results.py)&#91;[TaxOut](helm_api/models/tax_out.py), [ApiTaxErrorBody](helm_api/errors/api_tax_error.py)&#93;</code>

**On `Success`**: `payload` is <code>[TaxOut](helm_api/models/tax_out.py)</code> -- Successful Response

**On `Failure`**: `error` is <code>[ApiTaxErrorBody](helm_api/errors/api_tax_error.py)</code>

Mapped in first-match order -- an earlier row wins over a later range that also covers the status:

| Status | `error` is |
| --- | --- |
| 400 | <code>[ErrorOut](helm_api/models/error_out.py)</code> |
| 422 | <code>[HttpValidationError](helm_api/models/http_validation_error.py)</code> |
| anything unmapped | <code>[RawError](helm_api/core/results.py)</code> |

</dd>
</dl>

</dd>
</dl>

</details>

