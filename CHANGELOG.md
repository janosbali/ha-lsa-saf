# Changelog

## Unreleased

- Complete a dependency-free GOES ABI Fire/Hot Spot technical spike.
- Add strict GOES-18/19 FDC filename and timestamp validation plus fixed public
  bucket metadata without enabling any new runtime network access.
- Document that GOES is a Western Hemisphere option rather than a European LSA
  SAF replacement, together with the security, coverage, NetCDF, and resource
  gates required before a production adapter can be considered.

## 0.7.0

- Add an explainable, provider-neutral Active Fire Situation sensor with
  `normal`, `elevated`, `high`, `critical`, and `unknown` states.
- Keep Active Fire Situation separate from the environmental FRMv3 Fire Risk
  forecast; it evaluates only current detected fire activity.
- Score bounded signals from nearest distance, active incident count, observed
  FRP, approaching activity, increasing FRP, and increasing detection activity.
- Require a detection within 100 km for `high` and within 25 km plus multiple
  corroborating signals for `critical`.
- Return `unknown`, never `normal`, when satellite data is unavailable,
  delayed, or older than 60 minutes.
- Expose a compact reason list and contributing counts without publishing raw
  incident histories or presenting the result as an official emergency level.
- Add localized state names in all six supported languages and privacy-safe
  diagnostic output.
- Add tests for normal, elevated, high, critical, stale-data, and outage cases.

## 0.6.0

- Add a bounded 24-hour provider-neutral activity history that never appears as
  an unbounded Home Assistant state attribute.
- Add sensors for detections during the last 1/3/6 hours, aggregate FRP change
  during the last 1/3 hours, and new incidents during the last 24 hours.
- Replace repeated observations of the same satellite product instead of
  double-counting them, while preserving its original new-incident count.
- Add a Fire incident trend event entity for meaningful transitions to
  increasing intensity, increasing/decreasing activity, or approaching Home.
- Apply a persistent per-incident, per-event 60-minute cooldown in addition to
  the trend engine's minimum sample, tolerance, and hysteresis rules.
- Publish automation-friendly `lsa_saf_fire_trend` bus events with bounded
  incident metadata, source attribution, and product time.
- Add English, Hungarian, German, French, Spanish, and Italian entity names.
- Add tests for fixed time windows, duplicate products, storage bounds, trend
  transitions, and repeat-event suppression.

## 0.5.0

- Add a provider-neutral trend engine for incident FRP, detection/pixel
  activity, and distance from Home.
- Classify FRP and activity as increasing, stable, decreasing, or unknown, and
  distance as approaching, stable, receding, or unknown.
- Use linear regression across a 90-minute observation window instead of
  comparing only two consecutive satellite products.
- Require at least three samples spanning 20 minutes before reporting a trend.
- Apply absolute and relative noise tolerances plus half-threshold hysteresis
  to prevent rapid trend-state oscillation.
- Keep at most 37 compact samples per incident and expose only bounded trend
  summaries as Home Assistant attributes.
- Migrate existing v0.4 incident records automatically; their trends remain
  unknown until enough new observations arrive.
- Add regression tests for rising, falling, stable, insufficient-data,
  hysteresis, duplicate-product, and bounded-history behaviour.

## 0.4.0

- Replace the coordinator's inline same-fire deduplication with a separately
  tested, provider-neutral persistent incident tracker.
- Preserve stable incident IDs while tracking first/last seen time, duration,
  current and minimum distance, current and maximum FRP, current and maximum
  pixel count, total contributing detections, and maximum confidence.
- Add explicit `new`, `continuing`, `inactive`, and `ended` lifecycle states.
- Keep unmatched incidents inactive during the configured memory window instead
  of immediately treating a missing detection as an ended fire.
- Do not advance lifecycle or discard incident history during provider outages.
- Migrate existing stored track records in place without generating duplicate
  new-fire events or replacing existing map entity identities.
- Expose bounded incident metadata on map entities and nearest-fire attributes,
  plus lifecycle counts in privacy-safe diagnostics.
- Avoid double-counting detections when Home Assistant polls the same satellite
  product more than once.

## 0.3.1

- Add an automation-friendly active-fire provider status sensor with
  initializing, available, delayed, no-product, outage, and authentication
  states.
- Keep the status sensor available during provider failures and expose the
  provider, satellite, product, product timestamp, and local receipt timestamp.
- Classify MTG products older than 60 minutes as delayed while retaining their
  detections instead of treating valid stale data as an empty current result.
- Normalize authentication, no-product, and provider failures at the provider
  boundary so the common coordinator no longer depends on MTG exceptions.
- Preserve the last successful coordinator data and all stored tracks when a
  refresh fails.
- Extend privacy-safe diagnostics and all six translations with provider health.

## 0.3.0

- Add a provider-neutral `FireDetection` model with optional confidence,
  classification, quality, temperature, area, and source metadata.
- Add a common `ProviderSnapshot` and typed active-fire provider interface.
- Move MTG product normalization into a dedicated provider adapter while
  retaining the existing secure MTFRPPixel parser and authentication flow.
- Move distance and spatial clustering into a provider-neutral processing
  module without changing MTG radius, centroid, FRP, or confidence behaviour.
- Preserve all config entries, options, entity unique IDs, stored tracks,
  events, automations, and dashboards.
- Add regression tests for MTG field mapping, optional provider data, immutable
  provider snapshots, and clustering equivalence.

## 0.2.8

- Add privacy-safe Home Assistant config-entry diagnostics without credentials,
  Home coordinates, fire coordinates, source URLs, or place names.
- Replace the English device model label with the locale-neutral product name
  `MTG Active Fire / FRMv3`.
- Validate every bundled integration JSON and translation file in CI.
- Refresh release metadata and branding documentation.

## 0.2.7

- Add bundled Home Assistant brand icons for normal and high-DPI displays.
- Add complete French, German, Italian, and Spanish translations.
- Extend localized calendar forecast events to all supported languages.

## 0.2.6

- Remove expired fire-location entities directly from Home Assistant's entity
  registry so they no longer remain visible as unavailable controls.

## 0.2.5

- Replace nine-point regional-risk sampling with an offline scan of the full
  bounded FRMv3 map inside the configured circular monitoring radius.
- Improve spatial coverage to roughly one sample per few kilometres while
  reducing the typical WMS request count.
- Share the one-hour raw map cache between risk analysis and the camera so
  opening the preview does not repeat the same download.
- Deterministically stagger each installation's twelve-hour refresh over a
  one-hour window to avoid synchronized scheduled-polling load spikes.
- Decode and analyze PNG data outside Home Assistant's event loop and retain
  the existing response-size and image-dimension safety limits.

## 0.2.4

- Overlay country borders on the static FRMv3 forecast map using a compact,
  bundled Natural Earth 1:110m European boundary extract.
- Keep boundary rendering fully offline, with no API key, network request, or
  disclosure of the Home location.
- Validate the bundled geometry and render a contrasting halo so borders remain
  visible across every fire-risk color.
- Add a native localized ten-day fire-risk calendar entity so users can display
  the full outlook with Home Assistant's standard Calendar card.

## 0.2.3

- Make the official interactive FRMv3 viewer directly accessible from the LSA
  SAF device page and document a one-tap dashboard button.
- Separate the active-fire alert radius from the fire-risk forecast/map radius,
  while retaining the previous radius for upgraded installations until the new
  control is changed.
- Add a forecast-update timestamp sensor with availability, validity range,
  forecast length, and next planned refresh metadata.
- Add a ready-to-copy ten-day dashboard forecast and interactive-map layout.
- Update English and Hungarian names and descriptions for the new controls.

## 0.2.2

- Separate near-Home fire risk from the highest sampled risk in the full
  monitoring area so a large radius cannot be mistaken for property-level risk.
- Add a dedicated monitoring-area maximum-risk sensor and clarify event scope.
- Replace forecast-day values `0`–`9` with localized Today, Tomorrow, and
  in-N-days labels while preserving stored configuration compatibility.
- Annotate the FRMv3 map with its validity date, Home marker, prominent offline
  GeoNames settlements, and a localized five-level color legend.
- Expose a link to the official interactive LSA SAF ADAGUC WMS viewer without
  adding another map provider, API key, or coordinate disclosure.
- Remove expired fire markers from the entity registry at startup and detach
  dynamic map markers from the LSA SAF device Controls list.
- Add regression tests for local-versus-area risk and bounded PNG annotation.

## 0.2.1

- Fix startup on current Home Assistant releases by deriving the FRMv3 map
  entity from `Camera`, the supported camera platform base class.
- Initialize both the coordinator and camera base classes explicitly and serve
  forecast images with the correct `image/png` content type.
- Add a regression test that imports every declared integration platform.
- Install Home Assistant's pinned camera dependency in the test environment so
  the camera platform is exercised during CI.

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
