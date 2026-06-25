NGL runtime pack
================

The renderer vendors the official NGL standalone browser bundle `dist/ngl.js`
in this directory. Release images copy this source-tree runtime pack and verify
it during Docker build; Docker build does not download NGL.

Normal report use only needs TOML/JSON plus a results root. Local source-tree
full real-run tests also use this vendored pack; missing runtime is a hard
failure, not a network fetch.

Reports embed this runtime only when a `structure_viewer` component declares
`runtime = "ngl"`.
