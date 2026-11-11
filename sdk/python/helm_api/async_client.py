from __future__ import annotations

from functools import cached_property
from types import TracebackType

from typing_extensions import Self

from .apis.agent import AsyncAgent
from .apis.ai import AsyncAi
from .apis.commerce import AsyncCommerce
from .apis.dashboard import AsyncDashboard
from .apis.pooling import AsyncPooling
from .apis.proofs import AsyncProofs
from .apis.treasury import AsyncTreasury
from .base_client import DEFAULT_TIMEOUT, BaseHelmApiClient
from .core import (
    OPERATING_SYSTEM,
    PYTHON_RUNTIME,
    AsyncHttpClient,
    AsyncHttpx2Client,
    AsyncRawClient,
    LoggingOptionsOrDict,
    RetryOptionsOrDict,
    param,
)


class AsyncHelmApiClient(BaseHelmApiClient[AsyncRawClient]):
    def __init__(
        self,
        *,
        base_url: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        retry_options: int | RetryOptionsOrDict | None = None,
        logging_options: LoggingOptionsOrDict | None = None,
        custom_async_http_client: AsyncHttpClient | None = None,
    ) -> None:
        super().__init__(
            base_url=base_url, timeout=timeout, retry_options=retry_options, logging_options=logging_options
        )
        self._raw_client = AsyncRawClient(
            http_client=(
                custom_async_http_client if custom_async_http_client is not None else AsyncHttpx2Client(timeout=timeout)
            ),
            retry_options=self._retry_options,
            logging_options=self._logging_options,
            global_headers=[
                param[str]("User-Agent", "HelmApiClient/1.0.0 Python"),
                param[str]("X-APIMatic-Lang", "Python"),
                param[str]("X-APIMatic-Package-Version", "1.0.0"),
                param[str]("X-APIMatic-Gen-Version", "4.0.0"),
                param[str]("X-APIMatic-OS", OPERATING_SYSTEM),
                param[str]("X-APIMatic-Runtime", PYTHON_RUNTIME),
            ],
        )

    @cached_property
    def agent(self) -> AsyncAgent:
        return AsyncAgent(self._raw_client, self._server)

    @cached_property
    def ai(self) -> AsyncAi:
        return AsyncAi(self._raw_client, self._server)

    @cached_property
    def commerce(self) -> AsyncCommerce:
        return AsyncCommerce(self._raw_client, self._server)

    @cached_property
    def dashboard(self) -> AsyncDashboard:
        return AsyncDashboard(self._raw_client, self._server)

    @cached_property
    def pooling(self) -> AsyncPooling:
        return AsyncPooling(self._raw_client, self._server)

    @cached_property
    def proofs(self) -> AsyncProofs:
        return AsyncProofs(self._raw_client, self._server)

    @cached_property
    def treasury(self) -> AsyncTreasury:
        return AsyncTreasury(self._raw_client, self._server)

    async def aclose(self) -> None:
        await self._raw_client.http_client.aclose()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, exc_tb: TracebackType | None
    ) -> None:
        await self.aclose()


AsyncClient = AsyncHelmApiClient
