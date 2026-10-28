# PetDom pack: Juno

Juno is a warm, playful handler who is quietly firm. She talks to you like a pet she is very
fond of and fully expects to behave: praise comes with a head pat, mistakes get a patient
"try again, good pet". Everything is gentle and friendly, nothing explicit.

Apply it in **Settings > Look > Theme pack**.

## What it sets

| Part | Value |
|------|-------|
| Phrases | `phrases.csv` (28 phrases, easy / normal / hard / extreme) |
| Look | `PetDom` theme (amber, gold and rose on dark brown), Segoe UI, glow, no scanlines or glitch |
| Interface texts | `ui_texts` in `pack.json` (header, subtitle, button, error messages, lockout, wait) |
| Backgrounds | 3 original images in `backgrounds/` (`pawtrail`, `bokeh`, `toys`: dark and warm, easy on the phrase panel), one picked at random per lock |
| Audio | `audio/success.wav` (cheerful rising chirp), `audio/error.wav` (soft falling "boop boop"), both generated |
| Rules | 2 rounds, a typo does not reset progress, case-insensitive, no paste, 2 s before the button, 6 wrong attempts then a 20 s time out |
| Protections (opt-in) | strict mode and an idle lock after 30 minutes. Only applied when you tick the box *and* an emergency password is set |

A pack never changes the emergency password, auto-protection or the schedule.

## Where to put your own files

After you apply the pack, its files live in `%APPDATA%\PhraseLock\packs\petdom\`
(*Settings > Look > Theme pack > Open pack folder* opens it).

| What | Folder | Notes |
|------|--------|-------|
| Background images and GIFs | `backgrounds\` | Every `.png`, `.jpg`, `.webp`, `.bmp` or `.gif` here is used, one picked at random per lock. Add yours next to the defaults (or delete them), then apply the pack again. |
| Audio | `audio\` | Replace `success.wav` and `error.wav` (same names). `.wav` works best. |
| Phrases | `phrases.csv` | Columns `phrase,category,difficulty`. Your edits are kept when you re-apply the pack. |

In the source repository the same files are in `packs/petdom/`; anything you add there before
building ships inside `PhraseLock.exe`.
