# Asset rights and release boundary

`public/` is a workshop, not an automatic release payload. Two machine-readable files govern shipping:

- `config/runtime-assets.json` lists the files and directories copied into `.runtime-public/` before Vite builds. `production` is the release boundary; `developmentOnly` remains available through `npm run dev`.
- `config/asset-rights.json` records every audio file, its clearance state and the evidence still required.

Run `npm run rights:check` whenever audio changes. It fails if an audio file has no register entry or if production includes audio that is not explicitly approved. `npm run check` runs this in CI along with tests, manifest validation and the production build.

## Current audio decision

Two recordings are marked `owner-approved` and ship in production (2026-09-24, on Daniel's instruction):

- `assets/audio/ambience/manny-streets.mp3`, treated as Daniel's own field recording.
- `assets/audio/Ambient music/Popcorn.mp3`, a **third-party recording with no licence or written permission on record**. It is published as an owner decision; the takedown risk is the owner's. Record any licence evidence in `config/asset-rights.json` if it is obtained.

The other eight recordings remain `verification-required`: several filenames identify commercial or YouTube-derived sources, and the repository does not prove authorship or release permission for the rest. They stay available in local development only.

To clear an original recording, record the creator, date, consent/release basis and any attribution requirement in `config/asset-rights.json`, set `productionApproved` to `true`, and add the exact path to the production runtime manifest. For third-party work, keep the licence or written permission outside git if it contains private information, but record a stable evidence reference in the manifest.

Apply the same discipline to photography, fonts, branded garments and third-party 3D assets as those inventories mature. Do not treat online availability, a downloaded filename or use in a private prototype as permission to publish.
