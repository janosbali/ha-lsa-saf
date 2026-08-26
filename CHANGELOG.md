# Changelog

## 0.1.6

- Support fire-icon markers through the Home Assistant map card's `label_mode: icon` setting.
- Add optional OpenStreetMap Nominatim reverse geocoding for fire coordinates.
- Display a named feature and/or nearest settlement in each fire marker popup.
- Keep reverse geocoding disabled by default and never send Home coordinates or credentials.
- Cache place results per fire track, limit lookups to four per minute, reject redirects, and bound response time and size.
- Add tests for place-name parsing, sanitization, map attributes, and malformed or oversized responses.

## 0.1.5

- Add native Home Assistant `geo_location` entities for every active fire cluster.
- Expose distance, coordinates, FRP, peak FRP, confidence, acquisition time, pixel count, product time, and source URL on map entities.
- Retain fire markers for the configured same-fire memory period, then remove them automatically.
- Preserve stable map entity identities while a tracked fire moves within the configured same-fire matching radius.
- Prevent two simultaneous clusters from being assigned the same persisted track.
- Replace deprecated aiohttp BasicAuth request handling with an explicit encoded Authorization header.
- Add regression tests for map coordinates, state, attributes, and tracked-cluster updates.

## 0.1.4

- Restrict authenticated requests to the official HTTPS LSA SAF host and reject redirects.
- Add explicit connect/read/total HTTP timeouts and sanitized transport errors.
- Limit compressed downloads, bounded gzip expansion, CSV rows, columns, and field sizes.
- Reject duplicate CSV columns, implausible timestamps, and non-finite/out-of-range numeric values.
- Add CodeQL, Bandit, pip-audit, secret-pattern scanning, and Dependabot automation.
- Scope pip-audit to dependencies shipped by the integration instead of the non-runtime Home Assistant test harness.
- Add regression tests for URL, download, gzip-bomb, CSV-shape, and numeric validation.

## 0.1.3

- Added full config-flow, reauthentication, duplicate-account, error-recovery, and options-flow tests.
- Added pytest/coverage CI using the Home Assistant custom-component test harness.
- Added test requirements and pytest configuration.

## 0.1.2

- Add dedicated HACS and Hassfest GitHub Actions with scheduled validation.
- Validate against Python 3.14 in CI to follow current Home Assistant requirements.
- Add manual workflow dispatch support and minimal GitHub Actions permissions.
- Remove generated pytest/cache artifacts from the release package.
- Refresh version-specific setup text in translations and documentation.

## 0.1.1

- Validate credentials through the real MTFRPPixel product download path rather than the archive index.
- Add Home Assistant reauthentication flow for changed/expired LSA SAF credentials.
- Raise `ConfigEntryAuthFailed` during polling so Home Assistant automatically starts reauthentication.
- Avoid keeping separate plaintext username/password instance attributes in the HTTP client.

## 0.1.0

- Generalized the integration domain and repository to `lsa_saf` / `ha-lsa-saf`.
- Implemented MTG MTFRPPixel (LSA-509) active-fire ingestion.
- Added adjustable monitoring radius, confidence and FRP filters.
- Added fire-pixel clustering and persistent same-fire deduplication.
- Added `lsa_saf_new_fire` Home Assistant bus events and a New Active Fire event entity.
- Suppresses alerts for the initial snapshot on first setup.
- Added modular `products/` architecture.
- Added metadata scaffolding for FRMv3 Fire Risk Forecast and MTLST (LSA-007).
- Added English and Hungarian translations.
