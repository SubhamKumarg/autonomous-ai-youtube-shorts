
# 🎬 Autonomous AI YouTube Shorts Engine

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)
![Gemini API](https://img.shields.io/badge/Brain-Google%20Gemini%20API-orange?logo=google&logoColor=white)
![Edge-TTS](https://img.shields.io/badge/Voice-Edge%20Neural%20TTS-0078D7?logo=microsoft&logoColor=white)
![MoviePy](https://img.shields.io/badge/Render-MoviePy%2024fps-yellow)
![YouTube API](https://img.shields.io/badge/Upload-YouTube%20Data%20API%20v3-red?logo=youtube&logoColor=white)

An end-to-end, zero-cost autonomous content creation and publishing pipeline written in Python. With a single click of a desktop application, this engine conceptualizes viral short-form topics, writes structured 4-beat scripts, synthesizes emotion-modulated neural voiceovers with word-level synchronization, renders 1080x1920 vertical videos complete with audio-reactive equalizers and elastic pop-in captions, and publishes directly to YouTube Shorts without human intervention.

---

## 🌟 Visual Showcase & Aesthetic Design

This project is engineered to stop the scroll by mimicking top-tier professional short-form content creators:

| ⚡ Word-by-Word Yellow Captions | 📊 Audio-Reactive Equalizer & Ken Burns |
| :---------------------------------: | :-------------------------------------: |
| ![Caption Preview](https://raw.githubusercontent.com/SubhamKumarg/autonomous-ai-youtube-shorts/main/assets/preview-caption.png) | ![Equalizer Preview](https://raw.githubusercontent.com/SubhamKumarg/autonomous-ai-youtube-shorts/main/assets/preview-equalizer.png) |
| *Exact synchronization using `WordBoundary` timestamps with viral yellow text, black strokes & 3D drop shadows.* | *17-bar neon equalizer pulsing dynamically with speaker volume over cinematic photography.* |

* **🎙️ Interactive 4-Beat Emotional Pitch Modulation (`edge-tts`):** The narration is split into 4 distinct emotional beats:
  1. *The Hook:* High energy (`+12%` speed, `+4Hz` pitch) to capture attention immediately.
  2. *The Suspense:* Deeper, slower tone (`-4Hz`) to build tension.
  3. *The Twist:* Fast, punchy delivery for the reveal.
  4. *The Outro:* Upward inflection to prompt comments and engagement.

---

## 🏗️ Pipeline Architecture

```text
[Google Gemini API (Pydantic Schema)] 
       │
       ▼  (Generates 4 Story Beats, Title, SEO Tags & Photo Keywords)
[Edge-TTS Neural Synthesizer] 
       │
       ▼  (Modulates Pitch/Rate per Beat + Extracts Word-Level Timestamps)
[Wikimedia / Cinematic Visual Engine] 
       │
       ▼  (Fetches High-Res Photos + Applies Vignette & Ken Burns Pan)
[MoviePy + NumPy 24fps Compositor] 
       │
       ▼  (Composites Audio-Reactive Waveform + Yellow Word-by-Word Sprites)
[YouTube Data API v3 Uploader] ──► Live Public YouTube Short
