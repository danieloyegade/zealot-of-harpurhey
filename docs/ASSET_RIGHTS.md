# Asset rights and release boundary

`public/` is a workshop, not an automatic release payload. Two machine-readable files govern shipping:

- `config/runtime-assets.json` lists the files and directories copied into `.runtime-public/` before Vite builds. `production` is the release boundary; `developmentOnly` remains available through `npm run dev`.
- `config/asset-rights.json` records every audio file, its clearance state and the evidence still required.

Run `npm run rights:check` whenever audio changes. It fails if an audio file has no register entry or if production includes audio that is not explicitly approved. `npm run check` runs this in CI along with tests, manifest validation and the production build.

## Current audio decision

All ten recordings are marked `verification-required`. Several filenames identify commercial or YouTube-derived sources; the field recordings may be original project material, but the repository does not yet prove authorship or public-release permission. For that reason:

- all audio remains available in local development;
- no audio is copied into the production build;
- production instantiates no audio player, avoiding failed requests for excluded files.

To clear an original recording, record the creator, date, consent/release basis and any attribution requirement in `config/asset-rights.json`, set `productionApproved` to `true`, and add the exact path to the production runtime manifest. For third-party work, keep the licence or written permission outside git if it contains private information, but record a stable evidence reference in the manifest.

Apply the same discipline to photography, fonts, branded garments and third-party 3D assets as those inventories mature. Do not treat online availability, a downloaded filename or use in a private prototype as permission to publish.
