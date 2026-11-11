from __future__ import annotations

from functools import cached_property
from types import TracebackType

from typing_extensions import Self

from .apis.agent import Agent
from .apis.ai import Ai
from .apis.commerce import Commerce
from .apis.dashboard import Dashboard
from .apis.pooling import Pooling
from .apis.proofs import Proofs
from .apis.treasury import Treasury
from .base_client import DEFAULT_TIMEOUT, BaseHelmApiClient
from .core import (
    OPERATING_SYSTEM,
    PYTHON_RUNTIME,
    HttpClient,
    Httpx2Client,
    LoggingOptionsOrDict,
    RawClient,
    RetryOptionsOrDict,
    param,
)


class HelmApiClient(BaseHelmApiClient[RawClient]):
    def __init__(
        self,
        *,
        base_url: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        retry_options: int | RetryOptionsOrDict | None = None,
        logging_options: LoggingOptionsOrDict | None = None,
        custom_http_client: HttpClient | None = None,
    ) -> None:
        super().__init__(
            base_url=base_url, timeout=timeout, retry_options=retry_options, logging_options=logging_options
        )
        self._raw_client = RawClient(
            http_client=custom_http_client if custom_http_client is not None else Httpx2Client(timeout=timeout),
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
    def agent(self) -> Agent:
        return Agent(self._raw_client, self._server)

    @cached_property
    def ai(self) -> Ai:
        return Ai(self._raw_client, self._server)

    @cached_property
    def commerce(self) -> Commerce:
        return Commerce(self._raw_client, self._server)

    @cached_property
    def dashboard(self) -> Dashboard:
        return Dashboard(self._raw_client, self._server)

    @cached_property
    def pooling(self) -> Pooling:
        return Pooling(self._raw_client, self._server)

    @cached_property
    def proofs(self) -> Proofs:
        return Proofs(self._raw_client, self._server)

    @cached_property
    def treasury(self) -> Treasury:
        return Treasury(self._raw_client, self._server)

    def close(self) -> None:
        self._raw_client.http_client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, exc_tb: TracebackType | None
    ) -> None:
        self.close()


Client = HelmApiClient
