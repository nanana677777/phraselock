# Mistress pack: Mistress Vesper

Mistress Vesper is elegant, composed and exacting. She never raises her voice: courtesy, precision
and obedience are expected, and mistakes get a patient "again, properly". Everything is formal
and non-explicit.

Apply it in **Settings > Look > Theme pack**.

## What it sets

| Part | Value |
|------|-------|
| Phrases | `phrases.csv` (28 phrases, easy / normal / hard / extreme) |
| Look | `Mistress` theme (burgundy, gold and rose on near-black), Segoe UI, glow, no scanlines or glitch |
| Interface texts | `ui_texts` in `pack.json` (header, subtitle, button, error messages, lockout, wait, emergency unlock dialog and its 5 confirmation screens) |
| Backgrounds | 3 original images in `backgrounds/` (`velvet`, `filigree`, `keyhole`: dark and low-contrast, easy on the phrase panel), one picked at random per lock |
| Audio | `audio/success.wav` (two-note silver bell), `audio/error.wav` (two low knocks), both generated |
| Rules | 3 rounds, a typo resets progress, case-sensitive, no paste, 4 s before the button, 4 wrong attempts then a 45 s silence |
| Protections (opt-in) | strict mode and an idle lock after 20 minutes. Only applied when you tick the box *and* an emergency password is set |

A pack never changes the emergency password, auto-protection or the schedule.

## Where to put your own files

After you apply the pack, its files live in `%APPDATA%\PhraseLock\packs\mistress\`
(*Settings > Look > Theme pack > Open pack folder* opens it).

| What | Folder | Notes |
|------|--------|-------|
| Background images and GIFs | `backgrounds\` | Every `.png`, `.jpg`, `.webp`, `.bmp` or `.gif` here is used, one picked at random per lock. Add yours next to the defaults (or delete them), then apply the pack again. |
| Audio | `audio\` | Replace `success.wav` and `error.wav` (same names). `.wav` works best. |
| Phrases | `phrases.csv` | Columns `phrase,category,difficulty`. Your edits are kept when you re-apply the pack. |

In the source repository the same files are in `packs/mistress/`; anything you add there before
building ships inside `PhraseLock.exe`.
