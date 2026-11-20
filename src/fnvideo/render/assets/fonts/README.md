# Brand fonts

Unmodified font files from the Google Fonts repository (`github.com/google/fonts`, `ofl/`),
each under the SIL Open Font License 1.1 (license text alongside).

| File | Family | License |
|---|---|---|
| `SpaceGrotesk[wght].ttf` | Space Grotesk (display/headlines) | `OFL-spacegrotesk.txt` |
| `Inter[opsz,wght].ttf` | Inter (body, captions) | `OFL-inter.txt` |
| `IBMPlexMono-Regular.ttf`, `IBMPlexMono-Bold.ttf` | IBM Plex Mono (labels) | `OFL-ibmplexmono.txt` (Reserved Font Name "Plex") |

The files are embedded unmodified (no subsetting) as data URIs in each scene page, so the
Reserved Font Name clause is not triggered. Do not subset or rename them without re-reading
the OFL. Glyph coverage of all spec text is checked by `tests/test_fonts.py`.
