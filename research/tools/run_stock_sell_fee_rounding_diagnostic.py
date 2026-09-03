#!/usr/bin/env python3
"""Run the fee-rounding diagnostic using only documented /user/log query keys.

The diagnostic module predates the final OpenAPI review and contains an internal
legacy `sort` default. Current Torn API v2 6.6.1 does not document `sort` for
/user/log. This runner removes that key before any HTTP request and prevents it
from being imported from Torn pagination links, while leaving the frozen
post-confirmation calculations unchanged.
"""
from __future__ import annotations

from typing import Any, Mapping

import diagnose_stock_sell_fee_rounding as diagnostic
from torn_research import TornApiClient

DOCUMENTED_USER_LOG_QUERY_KEYS = frozenset({"log", "from", "to", "limit"})


def sanitize_query(path: str, query: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if query is None:
        return None
    copied = dict(query)
    if path.rstrip("/") == "/user/log":
        return {key: value for key, value in copied.items() if key in DOCUMENTED_USER_LOG_QUERY_KEYS}
    return copied


class DocumentedUserLogClient(TornApiClient):
    def get(self, path: str, query: Mapping[str, Any] | None = None):
        return super().get(path, sanitize_query(path, query))


def main() -> int:
    # Do not import any undocumented query key from _metadata.links.next.
    diagnostic.ALLOWED_NEXT_QUERY_KEYS = set(DOCUMENTED_USER_LOG_QUERY_KEYS)
    # diagnostic.run resolves TornApiClient from its module globals at runtime.
    diagnostic.TornApiClient = DocumentedUserLogClient
    return diagnostic.main()


if __name__ == "__main__":
    raise SystemExit(main())
