# Walkthrough video assets

Three short silent screen recordings power the `/walkthrough` page. They autoplay, loop, and have no audio — same pattern as wego-digest and axiom-valuation.

## Files expected here

```
01-run-screen.mp4         ~25s, ~3-6 MB, 1280×800
02-memo-synthesis.mp4     ~20s, ~3-5 MB, 1280×800
03-contrast.mp4           ~30s, ~4-7 MB, 1280×800
```

If a file is missing the walkthrough page renders a placeholder card with the recording instructions baked in — so the page never breaks, even pre-recording.

## How to record on macOS (5 minutes per video)

1. **Open Sentinel** in a clean Chrome window, maximized to a clean size — drag the window to ~1280px wide so the recording is consistent.
2. **Cmd + Shift + 5** opens the macOS screen-recording UI.
3. Click **"Record Selected Portion"**, drag a clean rectangle around the browser content (no chrome / no menu bar).
4. Click **Options** → uncheck microphone (silent). Save to `~/Desktop`.
5. Click **Record**. Perform the action sequence (see scripts below).
6. Click the recording icon in the menu bar (or **Cmd + Ctrl + Esc**) to stop.
7. Trim the start/end: open the resulting `.mov` in QuickTime → **Edit → Trim**.
8. Convert to web-optimized MP4 (smaller file, autoplay-friendly):

```bash
brew install ffmpeg   # one-time
ffmpeg -i ~/Desktop/Screen\ Recording.mov \
  -vcodec libx264 -crf 26 -preset slow -movflags +faststart \
  -an -vf "scale=1280:-2" \
  ~/Desktop/qatalyst-interview-demo/sentinel/static/videos/01-run-screen.mp4
```

The `-an` flag strips audio. The `-crf 26` keeps file size small without visible quality loss for a UI demo.

## Recording scripts

### 01-run-screen.mp4 (~25 seconds)

1. Start on the home page (`/`). Wait 2 seconds at the top so the hero is visible.
2. Scroll down to the "Screen a project" section. Pause briefly on the four sample-project cards.
3. Click **Cordillera Azul REDD+**.
4. Hold on the loading skeleton (four pulsing panels appearing) for ~3 seconds — this is the "feel the engine work" moment.
5. As the result populates, hold on the **verdict header** (🔴 HIGH social-license risk, composite 12) for 2-3 seconds.
6. Stop recording. Trim any dead air at start and end.

### 02-memo-synthesis.mp4 (~20 seconds)

1. Start with a Cordillera Azul result already on screen (run the screen first, then start recording).
2. Begin recording, slowly scroll down past the four evidence panels (territory, news, litigation, NGO).
3. Pause briefly on the dark forest-green **ESG PILLAR** band where Environmental + Governance appear.
4. Keep scrolling to the **IC-MEMO · ESG SAFEGUARDS SECTION** panel. The two-paragraph memo should be visible.
5. Hold on the memo text for 3-4 seconds so the viewer can read the first line.
6. Stop recording.

### 03-contrast.mp4 (~30 seconds)

1. Start on a Cordillera Azul result page (🔴 HIGH).
2. Start recording.
3. Scroll up to expose the **quick-compare pill bar** above the verdict.
4. Hover briefly on each pill, then click **🟢 Mikoko Pamoja**.
5. Hold on the loading skeleton for ~3 seconds.
6. Hold on the final 🟢 LOW result with all-zero panels for 3-4 seconds.
7. Optionally click 🔴 Kariba in the compare bar to show a second contrast.
8. Stop recording.

## If you don't want to record

Just leave this folder empty. The walkthrough page already shows clean placeholder cards with each video's purpose written on them — so it still tells the story end-to-end, just without the live motion.
