# Changelog

## 0.2.0

- Add the demonstration FRMv3 Fire Risk Map forecast for Europe.
- Add a localized enum sensor for today's sampled fire risk and a ten-day forecast attribute.
- Avoid urban `nodata` pixels by sampling Home and eight representative points within the monitoring radius.
- Add a day 0–9 selector and a standard Home Assistant camera entity for the selected forecast map.
- Add an event when today's risk rises to high, very high, or extreme.
- Keep FRMv3 updates independent and non-blocking so an outage cannot stop active-fire monitoring.
- Refresh risk data every 12 hours while caching map images for one hour.
- Enforce HTTPS, reject redirects, and bound WMS JSON and PNG response sizes and timeouts.

## 0.1.9

- Resolve the nearest settlement before publishing each new-fire event.
- Add concise localized `notification_title` and `notification_message` event fields.
- Use **Tűzészlelés riasztás** and a natural settlement-first message on Hungarian Home Assistant systems.
- Fall back to an English notification or a distance-only message when needed.
- Update the notification automation example to use the integration-provided localized text.

## 0.1.8

- Replace all Nominatim network lookups with the bundled GeoNames `cities500` database.
- Resolve nearest settlements entirely on the Home Assistant device with no API quota or coordinate disclosure.
- Remove the configurable geocoding endpoint, HTTP request code, rate limiting, backoff, and persistent geocoding cache.
- Add a compact read-only SQLite dataset with indexed bounded-box searches outside the event loop.
- Enable nearby settlement names by default while retaining the option to disable them.
- Migrate previously cached Nominatim names to fresh offline GeoNames results.
- Add GeoNames CC BY 4.0 attribution, deterministic dataset tooling, and offline lookup regression tests.

## 0.1.7

- Add a configurable HTTPS Nominatim reverse-geocoding endpoint for self-hosted and larger deployments.
- Add a shared 90-day coordinate cache so nearby or recurring fires reuse one place lookup.
- Limit the public Nominatim endpoint to 30 requests per hour and four requests per minute per installation.
- Serialize custom-endpoint requests and cap them at 240 per hour per installation.
- Back off for five minutes after transport failures and one hour after HTTP 429 or server errors.
- Limit the persistent place cache to 5,000 recent entries.
- Reject endpoint URLs containing credentials, query strings, fragments, non-HTTPS schemes, or unexpected paths.
- Add configuration, URL-validation, cache-reuse, and cache-expiry regression tests.

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
