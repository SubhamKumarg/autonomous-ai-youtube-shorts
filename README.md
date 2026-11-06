@'
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

* **⚡ Word-by-Word Pop-In Captions (`Pillow` + `NumPy`):** Each spoken word pops onto the screen in exact synchronization with the voiceover audio using `WordBoundary` timestamps. Words are styled in **viral bright yellow (`#FFE600`) with a thick 12px black stroke and 3D drop shadow**, animated with an elastic spring scale.
* **🎙️ Interactive 4-Beat Emotional Pitch Modulation (`edge-tts`):** Instead of a monotone robotic voice, the narration is split into 4 distinct emotional beats:
  1. *The Hook:* High energy (`+12%` speed, `+4Hz` pitch) to capture attention immediately.
  2. *The Suspense:* Deeper, slower tone (`-4Hz`) to build tension.
  3. *The Twist:* Fast, punchy delivery for the reveal.
  4. *The Outro:* Upward inflection to prompt comments and engagement.
* **📊 Audio-Reactive Real-Time Equalizer:** A 17-bar neon equalizer at the center of the screen pulses dynamically in sync with the speaker's vocal amplitude and frequencies.
* **🎨 Cinematic Ken Burns & Floating Embers:** Background scenes feature high-resolution real photography (sourced via Wikimedia Commons and Picsum) treated with dark vertical vignettes, smooth zoom/pan motions, camera flashes on beat transitions, and drifting luminous ember particles.

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





🚀 Complete Step-by-Step Installation Guide (For New Users)
Step 1: Install Prerequisites
Python 3.10+: Download and install Python from python.org. Crucial: Check the box that says "Add Python to PATH" during installation.

FFmpeg: Open your terminal and install FFmpeg:

Windows: winget install Gyan.FFmpeg

Linux / Mac: sudo apt install ffmpeg or brew install ffmpeg

Step 2: Clone the Repository
Open your terminal and clone the repository:

Bash
git clone [https://github.com/SubhamKumarg/autonomous-ai-youtube-shorts.git](https://github.com/SubhamKumarg/autonomous-ai-youtube-shorts.git)
cd autonomous-ai-youtube-shorts
Step 3: Install Dependencies
Install all required Python packages:

Bash
pip install -r requirements.txt
🔑 Getting Your Free API Keys & Credentials
1. Gemini API Key (Free Brain)
Go to Google AI Studio.

Click Create API Key and copy your key string.

Create a file named .env in your project folder and add your key:

Code snippet
GEMINI_API_KEY=your_actual_gemini_api_key_here
2. YouTube Data API v3 & OAuth Credentials (Auto-Uploader)
Go to the Google Cloud Console.

Create a new project named YTAutoUploader.

Search for YouTube Data API v3 in the top search bar and click Enable.

Go to APIs & Services -> OAuth consent screen:

Select External, click Create, fill in your App Name and Email, and save.

Under Audience / Test users, click + Add Users and enter your exact YouTube channel Gmail address.

Go to Clients (Credentials) -> + Create Credentials -> OAuth client ID:

Application type: Select Desktop app.

Click Create, then click Download JSON.

Rename that downloaded file to exactly client_secrets.json and place it directly inside your project root folder.

🖱️ Creating Your One-Click Desktop .EXE Launcher
To make the bot run with a single double-click without ever opening a terminal manually:

Open PowerShell inside your project folder.

Run this command to compile a standalone Windows .exe directly onto your Desktop:

PowerShell
$desk = [Environment]::GetFolderPath("Desktop"); $exePath = Join-Path $desk "OneClick_YouTube_Upload.exe"; $code = 'using System; using System.Diagnostics; class Program { static void Main() { Console.Title = "One-Click YouTube Bot Uploader"; Console.ForegroundColor = ConsoleColor.Yellow; Console.WriteLine("=== ONE-CLICK YOUTUBE SHORTS GENERATOR & UPLOADER ==="); Console.ResetColor(); ProcessStartInfo psi = new ProcessStartInfo("python", "bot.py"); psi.WorkingDirectory = Environment.CurrentDirectory; psi.UseShellExecute = false; Process p = Process.Start(psi); p.WaitForExit(); Console.WriteLine("\nDone! Closing window in 5 seconds..."); System.Threading.Thread.Sleep(5000); } }'; Add-Type -TypeDefinition $code -OutputAssembly "OneClick_YouTube_Upload.exe" -OutputType ConsoleApplication; Copy-Item "OneClick_YouTube_Upload.exe" $exePath -Force; Write-Host "`nSUCCESS! Placed OneClick_YouTube_Upload.exe on your Desktop!" -ForegroundColor Green
How to Use It:
Double-click OneClick_YouTube_Upload.exe on your Desktop anytime.

On the very first run, a browser window will open asking you to log into your YouTube account and grant upload permissions. Click Advanced -> Go to YTBot (unsafe) -> Continue. This creates a permanent token.json file.

From then on, every double-click will silently generate a fresh viral script, synthesize voice and captions, render the MP4 video, and publish it directly to your YouTube channel!

📂 Repository Structure
Plaintext
├── bot.py                     # Main generation, word-sync animation & upload engine
├── requirements.txt           # Pinned Python dependencies
├── .env                       # Local-only secret storage for GEMINI_API_KEY (Git-ignored)
├── .env.example               # Template environment file
├── client_secrets.json        # Google Cloud OAuth credentials (Git-ignored)
├── token.json                 # Saved YouTube login session token (Git-ignored)
└── README.md                  # Project documentation
🔒 Security Notice
This repository is pre-configured with a strict .gitignore file that ensures your .env API keys, client_secrets.json, and private YouTube token.json session files are never uploaded to GitHub.
'@ | Set-Content -Path "README.md" -Encoding UTF8

git add README.md
git commit -m "Docs: Complete professional README with installation and visual showcase"
git push -u origin main
Write-Host "`nSuccessfully pushed professional README to GitHub!" -ForegroundColor Green


### Step 3: Refresh Your GitHub Page
Once the command finishes running, go to your browser and refresh your repository page (`[https
