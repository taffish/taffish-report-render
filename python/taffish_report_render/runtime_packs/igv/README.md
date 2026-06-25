IGV runtime pack

The renderer expects a vendored IGV browser bundle in this directory before
release builds or full real-run tests.

Expected files:

- `igv.min.js` or `igv.js`
- `VERSION`
- `SOURCE.json`
- `LICENSE`

Docker build and `tests/test-real-run.sh` do not download this bundle. Updating
the runtime is a maintainer vendoring step: fetch the official package, extract
the standalone browser bundle, verify it, and record source/version/license
metadata here.
