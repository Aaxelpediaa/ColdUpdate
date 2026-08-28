# EvilHotUpdate

Same idea as `eviltranslation`, for JSON hot-update content instead of
lawnstrings: push a file, GitHub builds and hosts it, the game fetches it
live.

Content is split into variants -- a plain folder name under `raw/`, one per
cheat strength (`default`, `max_level`, ...). Each variant is a full,
self-contained bundle; which one a build points at is just which
`JsonUpdateServerConfig` URL its `SERVERCONFIG.rton` carries.

## How to use

It needs to be done in two steps:

- Get the hash the real server expects for your version:
  ```
  python fetch_real_hash.py 4.2.1
  ```
  Drop your JSON files into `raw/<variant>/4.2.1/` (create the variant
  folder if it's new), then build under that hash:
  ```
  python main.py 4.2.1 raw/<variant>/4.2.1 --hash <hash from above>
  ```
  Push. The GitHub Action rebuilds every `raw/<variant>/<version>/` folder
  under its own real hash and publishes to the `gh-pages` branch. Same as
  `eviltranslation`: go to `Settings -> Pages` and set the branch to
  `gh-pages` so your site actually serves it.

- Your files are now live at:
  ```
  https://<your_github_username>.github.io/EvilHotUpdate/<variant>/hotupdate/ad/level_shipping/4.2.1/<hash>.txt
  https://<your_github_username>.github.io/EvilHotUpdate/<variant>/hotupdate/ad/level_shipping/4.2.1/<hash>_md5.txt
  ```

## How to make it appear in game

Same file `eviltranslation` has you edit for `LawnStringServerConfig` --
decrypt `serverconfig.rton` out of `dynamic.rsb(.smf)` with Sen, find
`JsonUpdateServerConfig` this time, and point its four URLs at the variant
you want:

```json
"ReleaseFileInfoURL": "https://<your_github_username>.github.io/EvilHotUpdate/<variant>/",
"ShippingFileInfoURL": "https://<your_github_username>.github.io/EvilHotUpdate/<variant>/",
"ReleaseFileURL": "https://<your_github_username>.github.io/EvilHotUpdate/<variant>/",
"ShippingFileURL": "https://<your_github_username>.github.io/EvilHotUpdate/<variant>/"
```

Re-encode, repack, put it back. Launch the game and it fetches your bundle
from there -- whatever the real `V1270` response says is the current hash
and cv, unchanged; only the domain that hash is fetched from moves.

## A bundle replaces everything the real server would have served

The game only ever asks for one specific `<hash>.txt` per version, decided
entirely by the real server's own `V1270` response -- this project doesn't
touch that. Once `JsonUpdateServerConfig` points here instead, the real
server stops being consulted for file *content* at all, so a bundle has to
carry everything the game would have gotten from it: files you're not
modifying still need to be in `raw/<variant>/<version>/`, copied over
unedited, or the game silently loses whatever content the real server was
currently shipping for that version.
