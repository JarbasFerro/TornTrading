# TornTrading — Governance & Compliance Research

Status: **P0 research pass 1**  
Research date: 2026-09-02  
Questions covered: GOV-001 through GOV-007  
Stage 0 evidence policy applies.

## Executive conclusion

TornTrading can be built as a read-only decision-support userscript using Torn's API plus information from the Torn page the user has manually loaded and is actively viewing. Automatic Torn API calls are permitted; automatic non-API requests/actions to Torn are not. The script must not scrape Torn pages that are not actively viewed, extract data from unfocused Torn pages to send elsewhere or generate alerts, bypass CAPTCHA, or automatically perform game actions.

The safest initial architecture is therefore:

- Torn market data: automated calls to `api.torn.com` only.
- User portfolio data: official API only.
- Torn DOM: read/modify only on the currently visible stock page; never use the DOM as a background scraper.
- Trade execution: always a deliberate user action using Torn's native UI; TornTrading may calculate and prefill values locally but must not autonomously submit a buy/sell action.
- External financial data: may be fetched from non-Torn services, subject to those services' terms; do not bundle private Torn data or the API key into those requests.
- API key: keep local by default, use the minimum permission possible, never log or transmit it.

This architecture is approved as the compliance baseline for later work.

## Source hierarchy used

Primary sources:

1. Torn staff scripting rules, updated 2026-02-04: https://www.torn.com/forums.php?a=0&b=0&f=67&p=threads&t=16037108
2. Torn API documentation / acceptable usage: https://www.torn.com/api.html
3. Torn API Wiki: https://wiki.torn.com/wiki/API
4. Torn API v2 OpenAPI specification: https://www.torn.com/swagger/openapi.json

Secondary sources were used only to identify questions; they do not determine compliance.

## GOV-001 [P0] — Exact scripting rules

**Resolution: CLOSED**  
**Evidence class: MECHANIC**

Current Torn staff wording permits scripts/extensions/applications only when they rely on:

- data from Torn's API; or
- a Torn page the user manually loaded and is actively viewing.

The same rule prohibits:

- additional non-API requests to Torn that are not directly/manually initiated;
- scraping Torn pages not currently viewed;
- extracting data from unfocused Torn pages to send elsewhere, generate alerts, or draw attention to another window;
- CAPTCHA bypass;
- malicious or undisclosed functionality.

API-based software must also follow Torn's API acceptable-usage terms.

### TornTrading rule

All automated Torn network activity MUST use the official Torn API. No code path may call Torn page/action endpoints automatically.

## GOV-002 [P0] — Permitted assistance versus prohibited automation

**Resolution: CLOSED FOR ARCHITECTURE; execution edge cases remain subject to future compliance tests**  
**Evidence class: MECHANIC + conservative engineering interpretation**

The governing distinction is whether the script causes a non-API Torn request/game action without a direct manual user action.

### Permitted baseline

- Read data already present in the actively viewed stock page.
- Add overlays, charts, annotations, rankings and calculations.
- Sort/filter locally displayed information.
- Populate a local/custom input or calculate a suggested number of shares.
- Make Torn API calls automatically.
- Fetch independent external-market data automatically.

### Prohibited baseline

- Automatically click Torn's buy/sell/confirm controls.
- Automatically submit Torn forms.
- Automatically call Torn action/page endpoints outside the official API.
- Poll hidden Torn pages or endpoints.
- React to DOM changes by performing a Torn game action.
- Batch/loop native Torn actions from one user click.

### Product decision

TornTrading will not implement autonomous execution. A recommendation can end at `BUY`, `SELL`, `HOLD`, `WAIT`, suggested size, and explanation. Final execution remains native/manual.

## GOV-003 [P0] — Automatic Torn API refresh while on other pages

**Resolution: CLOSED**  
**Evidence class: MECHANIC**

The current scripting prohibition specifically targets automatic **non-API** Torn requests. Torn API calls are the supported automation channel. Torn's API documentation explicitly describes applications, extensions, graphing and notifications using API data.

### Constraint

API polling must respect:

- 100 requests/minute per user across all keys (current documented limit; can change);
- cache semantics;
- minimum-data principle in acceptable usage;
- error handling for rate limits and invalid/paused keys.

TornTrading should operate far below 100 requests/minute.

## GOV-004 [P0] — Automatically fetching external financial data

**Resolution: CLOSED WITH EXTERNAL-ToS CONDITION**  
**Evidence class: MECHANIC + scope interpretation**

Torn's scripting restriction concerns Torn API/page access. It does not prohibit independent requests to third-party financial-data services. Torn's API ToS examples also contemplate opt-in integrations with external services.

### Guardrails

External requests must:

- contain no Torn API key;
- contain no private Torn data unless explicitly required, disclosed and consented to;
- comply with the external provider's license/ToS;
- be declared in userscript permissions (`@connect`) and documentation;
- fail safely without changing Torn actions.

## GOV-005 [P0] — Sending API-derived data to an external backend

**Resolution: CLOSED AT POLICY LEVEL; architecture decision deferred**  
**Evidence class: MECHANIC**

Torn's acceptable-usage documentation states that API keys and data must be protected/confidential unless permitted by the key owner. Its published ToS examples explicitly describe remotely stored API data and service integrations when storage, sharing, purpose, key handling and access level are disclosed.

Therefore an external backend is not inherently prohibited, but it creates additional obligations.

### Approved default

Phase 1 must be **local-first**. The API key stays in isolated userscript storage and is sent only to Torn API via the `Authorization: ApiKey ...` header.

If a backend is later justified, it requires a separate architecture/compliance review covering:

- explicit opt-in;
- exact fields transmitted;
- retention/deletion;
- encryption in transit/at rest;
- who can access data;
- purpose limitation;
- no key transmission unless strictly necessary (prefer never);
- documented API ToS table/disclosure.

## GOV-006 [P0] — Minimum API access level

**Resolution: CLOSED FOR KNOWN FEATURES**  
**Evidence class: MECHANIC**

Current API v2 requirements:

| Capability | Endpoint | Access |
|---|---|---|
| All Torn stocks / current market fields | `GET /torn/stocks` | Public |
| Specific stock + chart history | `GET /torn/{stockId}/stocks` | Public |
| Torn server timestamp | `GET /torn/timestamp` | Public |
| Current user holdings + acquisition transactions + bonus progress | `GET /user/stocks` | Limited |
| Personal investment totals/historical personal stats | `GET /user/personalstats` | Public endpoint; private/full owner stats require Limited or higher |
| Detailed user logs | `GET /user/log` | Full |

### Product permission strategy

1. **Research/market-only mode:** Public key.
2. **Portfolio mode:** Limited/custom key containing only required selections.
3. **Event-level payout reconstruction:** Full key only if later proven sufficiently valuable; it must be optional.

Torn's API docs state custom keys can grant exact required selections. TornTrading should prefer custom/least-privilege access where practical.

## GOV-007 [P0] — API-key security controls

**Resolution: CLOSED AS MANDATORY SECURITY REQUIREMENTS**  
**Evidence class: MECHANIC + security design decision**

Torn explicitly requires keys and obtained data to be securely protected and confidential unless the owner permits sharing.

### Mandatory controls

- Store key in Tampermonkey/Greasemonkey isolated storage (`GM_setValue`/equivalent), not page DOM, URL, console output or analytics.
- Never commit a real key to GitHub, tests, fixtures or screenshots.
- Use API v2 header authentication: `Authorization: ApiKey <key>`; do not append the key to external URLs.
- Redact authorization headers from diagnostic/export output.
- No third-party telemetry containing the key.
- External financial-data requests must be constructed independently of the Torn key.
- Provide a clear `Forget API key` control.
- Treat API error 16 (insufficient access) as a permission issue, not a reason to ask automatically for a higher-privilege key.
- Default to the lowest access level needed for the enabled feature.
- If Full Access is ever requested, explain exactly why before accepting it.

## Compliance invariants for code review

Every PR containing network or DOM interaction must satisfy all of these:

1. All automatic Torn network calls target official API endpoints.
2. No automatic native Torn action request exists.
3. No background scraping of Torn DOM exists.
4. DOM-derived Torn data is processed only while the page is actively viewed.
5. No API key can reach logs, GitHub, external analytics or external financial providers.
6. `@connect` hosts are explicit and justified.
7. API permissions are least-privilege.
8. Trade submission remains manual.
9. Any new backend/data sharing requires a new governance review.

## Open compliance experiment

One future implementation-level question remains: precisely how Torn staff treats programmatically pre-filling a native buy/sell input before the user manually presses the native submit button. The architecture does not depend on this capability, so TornTrading must initially avoid native-form manipulation. If desired later, it will be submitted as a narrow compliance question/test rather than assumed safe.

## Decision

**APPROVED baseline.** GOV-001 through GOV-007 are sufficiently resolved to permit read-only research tooling and an API-based collector. Compliance is no longer blocking collection/analysis provided the invariants above are enforced.
