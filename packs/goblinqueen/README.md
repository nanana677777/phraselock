# Goblin Queen pack: Queen Rune

Queen Rune is a vain, greedy goblin queen who holds court on a gilded throne among her pigs. She talks
in lowercase with a lot of `~`, expects tribute and obedience and meets mistakes with a mocking
"again, piggie". It is all playful teasing, nothing explicit and no real money involved.

Apply it in **Settings > Look > Theme pack**.

## What it sets

| Part | Value |
|------|-------|
| Phrases | `phrases.csv` (28 phrases, easy / normal / hard / extreme) |
| Look | `Goblin Queen` theme (emerald, gold and royal purple on near-black), Segoe UI, glow, no scanlines or glitch |
| Interface texts | `ui_texts` in `pack.json` (header, subtitle, button, error messages, lockout, wait, emergency unlock dialog and its 5 confirmation screens) |
| Backgrounds | 3 original images in `backgrounds/` (`drapes`, `baroque`, `throne`: dark and low-contrast, easy on the phrase panel), one picked at random per lock |
| Audio | `audio/success.wav` (two coins clinking), `audio/error.wav` (a short low grunt, twice), both generated |
| Rules | 3 rounds, a typo resets progress, case-insensitive, no paste, 3 s before the button, 5 wrong attempts then a 40 s sty time-out |
| Protections (opt-in) | strict mode and an idle lock after 20 minutes. Only applied when you tick the box *and* an emergency password is set |

A pack never changes the emergency password, auto-protection or the schedule.

## Where to put your own files

After you apply the pack, its files live in `%APPDATA%\PhraseLock\packs\goblinqueen\`
(*Settings > Look > Theme pack > Open pack folder* opens it).

| What | Folder | Notes |
|------|--------|-------|
| Background images and GIFs | `backgrounds\` | Every `.png`, `.jpg`, `.webp`, `.bmp` or `.gif` here is used, one picked at random per lock. Add yours next to the defaults (or delete them), then apply the pack again. |
| Audio | `audio\` | Replace `success.wav` and `error.wav` (same names). `.wav` works best. |
| Phrases | `phrases.csv` | Columns `phrase,category,difficulty`. Your edits are kept when you re-apply the pack. |

In the source repository the same files are in `packs/goblinqueen/`; anything you add there before
building ships inside `PhraseLock.exe`.
