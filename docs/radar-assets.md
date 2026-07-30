# CS2 radar assets

Run `clutchiq-radar-assets detect` to locate Counter-Strike 2, then run
`clutchiq-radar-assets build` to extract official overview images and metadata
from the locally installed game into `clutchiq/assets/radar`.

## Source2Viewer provenance

By default ClutchIQ obtains the Windows x64 Source2Viewer CLI from the
[ValveResourceFormat GitHub project](https://github.com/ValveResourceFormat/ValveResourceFormat),
pinned to release tag **19.2**. It queries that tag's GitHub Releases API,
selects exactly one Windows x64 `Source2Viewer` asset, and downloads the
asset's immutable release URL—not a `latest` URL.

When GitHub publishes a `sha256:` asset digest, ClutchIQ verifies the download
against it before unpacking. When the release does not publish a digest,
ClutchIQ calculates SHA-256 for the exact downloaded release asset. In either
case it records the release repository, tag, asset name, URL, and hash in a
sidecar file beside the cached executable. Later runs hash the executable and
reuse it only when it matches that lock record. Failed downloads, digest
mismatches, and invalid archives never replace the managed executable.

`--source2viewer PATH` always overrides managed acquisition. It is intended for
offline operation, platforms without the managed Windows x64 binary, or a
locally vetted Source2Viewer installation.

### Updating the pin

Update `RELEASE_TAG` in `clutchiq/radar_assets/source2viewer.py` only after
reviewing the selected ValveResourceFormat release asset. Confirm its platform
and CLI compatibility, record its exact asset URL/name and SHA-256 (using the
published GitHub digest when available, otherwise an independently calculated
hash), and update the mocked release-API tests. Do not change to a moving
release URL or bypass hash verification.

## Generation and recovery

Optional discovery overrides are `--steam-root PATH` and `--cs2-root PATH`.
Use `clutchiq-radar-assets verify` to validate the generated manifest.
Generated images originate from the user's CS2 installation. Do not
redistribute Valve assets unless their licence permits it. The generator stages
output and only replaces `maps.json` after successful validation; retain the
prior assets when a CS2 or tool update causes extraction failures.
