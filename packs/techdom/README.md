# TechDom pack: Vex

Vex is a calm, precise, dry-witted systems administrator. She never raises her voice and
treats you as a misconfigured device she is patiently bringing into compliance. Praise is
rare and deadpan; every mistake is simply "logged".

Apply it in **Settings > Look > Theme pack**.

## What it sets

| Part | Value |
|------|-------|
| Phrases | `phrases.csv` (28 phrases, easy / normal / hard / extreme) |
| Look | `TechDom` theme (cyan and green on near-black), Consolas, scanlines, glow, glitch on errors |
| Interface texts | `ui_texts` in `pack.json` (header, subtitle, button, error messages, lockout, wait) |
| Backgrounds | 3 original images in `backgrounds/` (`grid`, `circuit`, `datastream`: dark cyan/green, easy on the phrase panel), one picked at random per lock |
| Audio | `audio/success.wav`, `audio/error.wav` (short generated beeps) |
| Rules | 2 rounds, reset on typo, no paste, 3 s before Submit, 5 wrong attempts then a 30 s lockout |
| Protections (opt-in) | strict mode and an idle lock after 20 minutes. Only applied when you tick the box *and* an emergency password is set |

A pack never changes the emergency password, auto-protection or the schedule.

## Where to put your own files

After you apply the pack, its files live in:

```
%APPDATA%\PhraseLock\packs\techdom\
```

(*Settings > Look > Theme pack > Open pack folder* opens it.)

| What | Folder | Notes |
|------|--------|-------|
| Background images and GIFs | `backgrounds\` | The three default images are already there. Every `.png`, `.jpg`, `.webp`, `.bmp` or `.gif` in this folder is used, one picked at random per lock. Add your own next to them (or delete the defaults), then apply the pack again. |
| Audio | `audio\` | Replace `success.wav` and `error.wav` with your own (same names). `.wav` works best. |
| Phrases | `phrases.csv` | Columns `phrase,category,difficulty`. Your edits are kept when you re-apply the pack. |

In the source repository the same files are in `packs/techdom/`: drop images or GIFs in
`backgrounds/` and sounds in `audio/` before building, and they ship inside `PhraseLock.exe`.
