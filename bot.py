import os
import io
import sys
import time
import json
import gc
import math
import random
import inspect
import socket
import ssl
import urllib.request
import urllib.parse
import asyncio
import numpy as np
import requests
from google import genai
from pydantic import BaseModel
import edge_tts
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from moviepy.editor import VideoClip, AudioFileClip, concatenate_audioclips
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# --- 0. BYPASS BROKEN ISP/WINDOWS DNS USING GOOGLE & CLOUDFLARE DoH ---
_orig_getaddrinfo = socket.getaddrinfo
_dns_cache = {}

def _custom_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    try:
        return _orig_getaddrinfo(host, port, family, type, proto, flags)
    except socket.gaierror:
        if host not in _dns_cache:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            for doh_url in [
                f"https://8.8.8.8/resolve?name={host}&type=A",
                f"https://1.1.1.1/dns-query?name={host}&type=A",
            ]:
                try:
                    req = urllib.request.Request(doh_url, headers={"Accept": "application/dns-json"})
                    with urllib.request.urlopen(req, timeout=5, context=ctx) as resp:
                        data = json.loads(resp.read().decode())
                        for ans in data.get("Answer", []):
                            if ans.get("type") == 1:
                                _dns_cache[host] = ans["data"]
                                break
                    if host in _dns_cache:
                        break
                except Exception:
                    continue
        if host in _dns_cache:
            return _orig_getaddrinfo(_dns_cache[host], port, family, type, proto, flags)
        raise

socket.getaddrinfo = _custom_getaddrinfo

# --- 1. CONFIGURATION ---
from dotenv import load_dotenv
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")  #[cite: 4]
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]  #[cite: 4]

# Clicking Desktop .EXE runs 1 cycle and closes cleanly. Pass --loop for 24/7 mode.
RUN_24_7_LOOP = "--loop" in sys.argv
HOURS_BETWEEN_UPLOADS = 4.5

VOICE_POOL = [
    "en-US-AndrewMultilingualNeural",
    "en-US-BrianMultilingualNeural",
    "en-US-ChristopherNeural",
]

# Interactive Pitch & Speed per Story Beat (Hook -> Suspense -> Twist -> Outro)
BEAT_VOICE_PROFILES = [
    ("+12%", "+4Hz"),   # Beat 1 (Hook): High energy, excited pitch to stop the scroll
    ("+3%", "-4Hz"),    # Beat 2 (Suspense): Deeper, slower, mysterious tone
    ("+10%", "+3Hz"),   # Beat 3 (Climax/Twist): Fast, punchy reveal
    ("+7%", "+5Hz"),    # Beat 4 (Interactive Question): Upward inflection to trigger comments
]


class StoryBeat(BaseModel):
    spoken_line: str
    search_keyword: str


class ShortPlan(BaseModel):
    category_badge: str
    title: str
    description: str
    beats: list[StoryBeat]
    tags: list[str]


# --- 2. GENERATE 4-BEAT INTERACTIVE SCRIPT WITH GEMINI ---
def generate_plan() -> ShortPlan:
    print("\n[1/5] Generating interactive 4-beat viral script with Gemini...")
    client = genai.Client(api_key=GEMINI_API_KEY)
    prompt = (
        "Create a gripping 30-second YouTube Short about a mind-blowing fact in psychology, space, human body, or history. "
        f"Unique seed: {time.time()}. "
        "Provide:\n"
        "1) category_badge: 2-word uppercase category (e.g. 'DARK PSYCHOLOGY', 'SPACE SECRET', 'BRAIN HACK').\n"
        "2) title: Catchy curiosity-gap title under 58 chars.\n"
        "3) description: 2-sentence description.\n"
        "4) beats: Exactly 4 story beats that form a 65-75 word spoken script:\n"
        "   - Beat 1 (Hook): Shocking question or statement (15-18 words).\n"
        "   - Beat 2 (Suspense): Deepening the mystery (16-20 words).\n"
        "   - Beat 3 (Twist): The mind-blowing scientific/historical truth (18-22 words).\n"
        "   - Beat 4 (Interactive Outro): A direct question asking viewers what they would do (12-16 words).\n"
        "   Each beat needs 'spoken_line' (plain spoken words only, no emojis) and 'search_keyword' (1-2 simple concrete nouns for photography like 'galaxy', 'human eye', 'lightning', 'ocean', 'clock').\n"
        "5) tags: 5 SEO tags."
    )

    candidate_models = [
        "gemini-3.5-flash-lite",
        "gemini-3.8-flash-lite",
        "gemini-3.8-flash",
        "gemini-3.5-flash",
        "gemini-3.8-pro",
    ]

    try:
        for m in client.models.list():
            name = m.name.replace("models/", "")
            if (
                "gemini" in name
                and ("flash" in name or "pro" in name)
                and "tts" not in name
                and "image" not in name
                and "embedding" not in name
            ):
                if name not in candidate_models:
                    candidate_models.append(name)
    except Exception:
        pass

    for model_name in candidate_models:
        for attempt in range(2):
            try:
                print(f"   -> Trying model: {model_name} (attempt {attempt + 1})...")
                res = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config={
                        "response_mime_type": "application/json",
                        "response_schema": ShortPlan,
                    },
                )
                print(f"   -> Success with {model_name}!")
                plan = ShortPlan.model_validate_json(res.text)
                with open("last_plan.json", "w", encoding="utf-8") as f:
                    f.write(plan.model_dump_json(indent=2))
                return plan
            except Exception as e:
                err_msg = str(e)
                if "404" in err_msg or "NOT_FOUND" in err_msg or "not supported" in err_msg:
                    break
                print(f"   -> Model busy ({err_msg[:60]}...). Switching in 4s...")
                time.sleep(4)

    raise RuntimeError("All Gemini models are currently busy. Wait 60 seconds and run again.")


# --- 3. INTERACTIVE PITCH VOICEOVER + EXACT WORD-BY-WORD TIMESTAMPS ---
async def synthesize_beat_with_words(
    text: str, voice: str, rate: str, pitch: str, out_mp3: str
) -> list[dict]:
    kwargs = {"text": text, "voice": voice, "rate": rate, "pitch": pitch}
    sig = inspect.signature(edge_tts.Communicate.__init__)
    if "boundary" in sig.parameters:
        kwargs["boundary"] = "WordBoundary"

    comm = edge_tts.Communicate(**kwargs)
    word_events = []

    with open(out_mp3, "wb") as audio_file:
        async for chunk in comm.stream():
            ctype = chunk.get("type")
            if ctype == "audio":
                audio_file.write(chunk["data"])
            elif ctype == "WordBoundary":
                w_text = chunk.get("text", "").strip()
                if w_text:
                    start_s = chunk["offset"] / 10_000_000.0
                    dur_s = max(chunk["duration"] / 10_000_000.0, 0.08)
                    word_events.append({"word": w_text, "start": start_s, "dur": dur_s})
    return word_events


def build_interactive_voiceover(plan: ShortPlan, final_audio_path="voice.mp3") -> tuple[list[dict], list[float]]:
    chosen_voice = random.choice(VOICE_POOL)
    print(f"[2/5] Synthesizing interactive pitch-modulated voice ({chosen_voice})...")

    beats = list(plan.beats)[:4]
    while len(beats) < 4:
        beats.append(StoryBeat(spoken_line="What do you think about this?", search_keyword="mystery"))

    all_words = []
    beat_clips = []
    beat_durations = []
    current_time_offset = 0.0

    for idx, beat in enumerate(beats):
        rate, pitch = BEAT_VOICE_PROFILES[idx % len(BEAT_VOICE_PROFILES)]
        temp_mp3 = f"beat_{idx}.mp3"
        raw_events = asyncio.run(
            synthesize_beat_with_words(beat.spoken_line, chosen_voice, rate, pitch, temp_mp3)
        )

        clip = AudioFileClip(temp_mp3)
        dur = clip.duration
        beat_clips.append(clip)
        beat_durations.append(dur)

        raw_tokens = [w.strip() for w in beat.spoken_line.split() if w.strip()]
        if len(raw_events) >= max(1, len(raw_tokens) // 2):
            for j, ev in enumerate(raw_events):
                start_abs = current_time_offset + ev["start"]
                if j + 1 < len(raw_events):
                    end_abs = current_time_offset + raw_events[j + 1]["start"]
                else:
                    end_abs = current_time_offset + max(ev["start"] + ev["dur"], dur - 0.08)
                all_words.append({
                    "word": ev["word"].upper(),
                    "start": start_abs,
                    "end": max(start_abs + 0.08, end_abs),
                    "beat": idx,
                })
        else:
            weights = []
            for tok in raw_tokens:
                pause_bonus = 2.5 if any(p in tok for p in [".", "?", "!", ",", "â€”", "-"]) else 0.0
                weights.append(max(len(tok), 2) + pause_bonus)
            total_w = sum(weights) or 1.0
            usable_dur = max(0.2, dur - 0.12)
            t_cursor = current_time_offset + 0.04
            for tok, w in zip(raw_tokens, weights):
                w_dur = usable_dur * (w / total_w)
                all_words.append({
                    "word": tok.upper(),
                    "start": t_cursor,
                    "end": t_cursor + w_dur,
                    "beat": idx,
                })
                t_cursor += w_dur

        current_time_offset += dur

    combined = concatenate_audioclips(beat_clips)
    combined.write_audiofile(final_audio_path, fps=44100, logger=None)
    for c in beat_clips:
        c.close()
    combined.close()

    for idx in range(len(beats)):
        try:
            os.remove(f"beat_{idx}.mp3")
        except OSError:
            pass

    print(f"   -> Synced {len(all_words)} spoken words across 4 emotional pitch shifts!")
    return all_words, beat_durations


# --- 4. FETCH HIGH-RES THEMATIC BACKGROUNDS ---
def fetch_background_image(keyword: str, index: int, accent_color: tuple) -> Image.Image:
    headers = {"User-Agent": "YouTubeShortsCreatorBot/3.0 (https://example.com; contact@example.com)"}
    try:
        q = urllib.parse.quote(f"filetype:bitmap {keyword}")
        wiki_url = (
            f"https://commons.wikimedia.org/w/api.php?action=query&generator=search"
            f"&gsrsearch={q}&gsrnamespace=6&gsrlimit=8&prop=imageinfo&iiprop=url"
            f"&iiurlwidth=1280&format=json"
        )
        r = requests.get(wiki_url, headers=headers, timeout=8).json()
        pages = r.get("query", {}).get("pages", {})
        img_urls = []
        for p in pages.values():
            info = p.get("imageinfo", [{}])[0]
            u = info.get("thumburl") or info.get("url")
            if u and any(u.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png"]):
                img_urls.append(u)
        if img_urls:
            chosen = random.choice(img_urls)
            img_bytes = requests.get(chosen, headers=headers, timeout=8).content
            im = Image.open(io.BytesIO(img_bytes)).convert("RGB")
            if im.width >= 400 and im.height >= 400:
                print(f"   -> [Beat {index+1}] Loaded real photo for '{keyword}'")
                return im
    except Exception:
        pass

    try:
        seed = int(time.time() * 100) + index * 99
        pic_url = f"https://picsum.photos/seed/{seed}/1080/1920"
        img_bytes = requests.get(pic_url, headers=headers, timeout=8).content
        im = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        print(f"   -> [Beat {index+1}] Loaded high-contrast cinematic background")
        return im
    except Exception:
        pass

    im = Image.new("RGB", (1080, 1920), (10, 12, 24))
    draw = ImageDraw.Draw(im)
    for _ in range(35):
        x, y = random.randint(0, 1080), random.randint(0, 1920)
        rad = random.randint(80, 420)
        draw.ellipse([x - rad, y - rad, x + rad, y + rad], fill=accent_color)
    return im.filter(ImageFilter.GaussianBlur(radius=95))


def prepare_cinematic_canvas(bg_raw: Image.Image) -> np.ndarray:
    target_w, target_h = 1260, 2240
    src_ratio = bg_raw.width / bg_raw.height
    tgt_ratio = target_w / target_h
    if src_ratio > tgt_ratio:
        new_h = target_h
        new_w = int(new_h * src_ratio)
    else:
        new_w = target_w
        new_h = int(new_w / src_ratio)

    bg = bg_raw.resize((new_w, new_h), Image.BILINEAR)
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    bg = bg.crop((left, top, left + target_w, top + target_h))

    bg = ImageEnhance.Contrast(bg).enhance(1.22)
    bg = ImageEnhance.Color(bg).enhance(1.18)
    bg = ImageEnhance.Brightness(bg).enhance(0.62)

    arr = np.array(bg, dtype=np.float32)
    y_coords = np.linspace(-1.0, 1.0, target_h)[:, None, None]
    vignette = 1.0 - 0.55 * (y_coords ** 2)
    arr = np.clip(arr * vignette, 0, 255).astype(np.uint8)
    return arr


# --- 5. PRE-RENDER YELLOW + BLACK STROKE WORD SPRITES ---
def load_bold_font(size: int) -> ImageFont.FreeTypeFont:
    for font_name in ["impact.ttf", "arialbd.ttf", "segoeuib.ttf", "calibrib.ttf"]:
        try:
            return ImageFont.truetype(font_name, size)
        except IOError:
            continue
    return ImageFont.load_default()


def render_yellow_word_sprite(word_text: str, font_big: ImageFont.FreeTypeFont) -> Image.Image:
    clean = word_text.strip()
    font = font_big if len(clean) <= 10 else load_bold_font(int(125 * (10 / max(len(clean), 10))))

    canvas_w, canvas_h = 1000, 300
    sprite = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(sprite)

    bbox = draw.textbbox((0, 0), clean, font=font, stroke_width=12)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = (canvas_w - tw) // 2 - bbox[0]
    ty = (canvas_h - th) // 2 - bbox[1]

    # Deep Black 3D Drop Shadow
    draw.text(
        (tx + 8, ty + 10),
        clean,
        font=font,
        fill=(0, 0, 0, 225),
        stroke_width=12,
        stroke_fill=(0, 0, 0, 225),
    )
    # Bright Viral Yellow (#FFE600) with Thick Black Stroke
    draw.text(
        (tx, ty),
        clean,
        font=font,
        fill=(255, 232, 0, 255),
        stroke_width=12,
        stroke_fill=(0, 0, 0, 255),
    )
    return sprite


def render_top_header_overlay(badge: str, title: str) -> tuple[np.ndarray, np.ndarray]:
    ui = Image.new("RGBA", (1080, 420), (0, 0, 0, 0))
    draw = ImageDraw.Draw(ui)
    badge_font = load_bold_font(34)
    title_font = load_bold_font(44)

    draw.rounded_rectangle([70, 95, 490, 162], radius=20, fill=(255, 232, 0, 245))
    draw.text((98, 108), badge.upper()[:22], fill=(0, 0, 0, 255), font=badge_font)

    draw.text(
        (70, 185),
        title.upper()[:34],
        font=title_font,
        fill=(255, 255, 255, 255),
        stroke_width=5,
        stroke_fill=(0, 0, 0, 255),
    )
    arr = np.array(ui)
    return arr[:, :, :3].astype(np.float32), (arr[:, :, 3:4] / 255.0).astype(np.float32)


# --- 6. BUILD 24FPS ANIMATED VIDEO WITH AUDIO-REACTIVE WAVEFORM & WORD POP ---
def build_animated_video(
    plan: ShortPlan,
    words_timeline: list[dict],
    beat_durations: list[float],
    audio_file="voice.mp3",
    out="final_short.mp4",
):
    print("[3/5] Preparing full-screen photography, floating embers & yellow word sprites...")
    audio = AudioFileClip(audio_file)
    total_dur = audio.duration

    accents = [
        (255, 232, 0),    # Viral Yellow
        (0, 245, 212),    # Cyber Cyan
        (255, 77, 109),   # Neon Rose
        (168, 85, 247),   # Electric Purple
    ]

    beats = list(plan.beats)[:4]
    canvases = []
    for i, b in enumerate(beats):
        raw_im = fetch_background_image(b.search_keyword, i, accents[i % len(accents)])
        canvases.append(prepare_cinematic_canvas(raw_im))

    beat_end_times = []
    acc_t = 0.0
    for d in beat_durations:
        acc_t += d
        beat_end_times.append(acc_t)

    big_font = load_bold_font(125)
    word_sprites = {}
    for w_item in words_timeline:
        w_str = w_item["word"]
        if w_str not in word_sprites:
            word_sprites[w_str] = render_yellow_word_sprite(w_str, big_font)

    header_rgb, header_a = render_top_header_overlay(plan.category_badge, plan.title)

    fps = 24
    num_frames = int(total_dur * fps) + 5
    voice_energy = np.zeros(num_frames, dtype=np.float32)
    try:
        snd_arr = audio.to_soundarray(fps=22050)
        if snd_arr.ndim > 1:
            snd_arr = snd_arr.mean(axis=1)
        samples_per_frame = max(1, int(22050 / fps))
        for f_idx in range(num_frames):
            chunk = snd_arr[f_idx * samples_per_frame : (f_idx + 1) * samples_per_frame]
            if len(chunk) > 0:
                voice_energy[f_idx] = float(np.sqrt(np.mean(chunk ** 2)))
        max_e = float(np.max(voice_energy)) or 1.0
        voice_energy = np.clip(voice_energy / (max_e * 0.75), 0.08, 1.0)
    except Exception:
        voice_energy[:] = 0.5

    particles = [
        {
            "x": random.randint(60, 1020),
            "y": random.randint(0, 1920),
            "speed": random.uniform(55.0, 130.0),
            "r": random.randint(4, 9),
        }
        for _ in range(22)
    ]

    def make_frame(t):
        b_idx = 0
        b_start = 0.0
        for idx, b_end in enumerate(beat_end_times):
            if t <= b_end or idx == len(beat_end_times) - 1:
                b_idx = idx
                break
            b_start = b_end
        b_dur = max(0.1, beat_durations[b_idx] if b_idx < len(beat_durations) else 5.0)
        b_prog = min(max((t - b_start) / b_dur, 0.0), 1.0)

        bg_c = canvases[b_idx % len(canvases)]

        # 1) Smooth Ken Burns Zoom + Pan across 1260x2240 canvas
        if b_idx % 2 == 0:
            crop_w = int(1260 - 170 * b_prog)
            crop_h = int(2240 - 300 * b_prog)
            x0 = int((1260 - crop_w) * (0.3 + 0.4 * b_prog))
        else:
            crop_w = int(1090 + 170 * b_prog)
            crop_h = int(1940 + 300 * b_prog)
            x0 = int((1260 - crop_w) * (0.7 - 0.4 * b_prog))
        y0 = (2240 - crop_h) // 2

        cropped = bg_c[y0 : y0 + crop_h, x0 : x0 + crop_w]
        frame_pil = Image.fromarray(cropped).resize((1080, 1920), Image.BILINEAR)
        frame = np.array(frame_pil, dtype=np.float32)

        # 2) Subtle Camera Flash on Beat Transitions
        if (t - b_start) < 0.15 and b_idx > 0:
            flash = ((0.15 - (t - b_start)) / 0.15) * 65.0
            frame = np.clip(frame + flash, 0, 255)

        # 3) Blend Top Header Badge
        frame[:420, :] = frame[:420, :] * (1.0 - header_a) + header_rgb * header_a

        # 4) Floating Glowing Embers
        for pt in particles:
            py = int((pt["y"] - t * pt["speed"]) % 1920)
            px = int(pt["x"] + math.sin(t * 2.5 + pt["r"]) * 18)
            r = pt["r"]
            if 10 <= py < 1910 and 10 <= px < 1070:
                frame[py - r : py + r, px - r : px + r] = np.clip(
                    frame[py - r : py + r, px - r : px + r] * 0.4 + np.array([255, 232, 0]) * 0.6,
                    0,
                    255,
                )

        # 5) Audio-Reactive Equalizer Bars
        f_idx = min(int(t * fps), len(voice_energy) - 1)
        energy = float(voice_energy[f_idx])
        num_bars = 17
        bar_spacing = 28
        start_x = 540 - (num_bars * bar_spacing) // 2
        base_y = 1230
        for b_i in range(num_bars):
            dist_center = abs(b_i - num_bars // 2) / (num_bars / 2.0)
            wave = abs(math.sin(t * 16.0 + b_i * 0.7))
            bar_h = int(12 + energy * (1.1 - 0.55 * dist_center) * wave * 95)
            bx = start_x + b_i * bar_spacing
            frame[base_y - bar_h - 3 : base_y + bar_h + 3, bx - 3 : bx + 15] = (0, 0, 0)
            frame[base_y - bar_h : base_y + bar_h, bx : bx + 12] = (255, 232, 0)

        # 6) Word-by-Word Yellow + Black Stroke Pop-In Caption
        active_word = None
        for w_item in words_timeline:
            if w_item["start"] <= t <= w_item["end"]:
                active_word = w_item
                break

        if active_word is not None:
            sprite = word_sprites[active_word["word"]]
            age = max(0.0, t - active_word["start"])
            if age < 0.06:
                scale = 0.72 + (age / 0.06) * 0.42
            elif age < 0.12:
                scale = 1.14 - ((age - 0.06) / 0.06) * 0.14
            else:
                scale = 1.0 + 0.03 * energy

            sw = max(40, int(sprite.width * scale))
            sh = max(20, int(sprite.height * scale))
            scaled_sprite = sprite.resize((sw, sh), Image.BILINEAR)
            sp_arr = np.array(scaled_sprite, dtype=np.float32)

            cx, cy = 540, 960
            x1 = max(0, cx - sw // 2)
            y1 = max(0, cy - sh // 2)
            x2 = min(1080, x1 + sw)
            y2 = min(1920, y1 + sh)

            crop_sp = sp_arr[: (y2 - y1), : (x2 - x1)]
            sp_rgb = crop_sp[:, :, :3]
            sp_a = crop_sp[:, :, 3:4] / 255.0

            frame[y1:y2, x1:x2] = frame[y1:y2, x1:x2] * (1.0 - sp_a) + sp_rgb * sp_a

        # 7) Bottom Progress Bar
        prog_w = max(8, min(int(940 * (t / total_dur)), 940))
        frame[1815:1831, 70:1010] = (0, 0, 0)
        frame[1818:1828, 70 : 70 + prog_w] = (255, 232, 0)

        return frame.astype(np.uint8)

    print("[4/5] Rendering 24fps word-synced MP4 video...")
    final_clip = VideoClip(make_frame, duration=total_dur).set_audio(audio)
    final_clip.write_videofile(out, fps=fps, codec="libx264", audio_codec="aac")
    audio.close()
    final_clip.close()


# --- 7. UPLOAD DIRECTLY TO YOUTUBE (SMART CHANNEL LIMIT & FILE-LOCK SAFE) ---
def upload_video(plan: ShortPlan, file_path="final_short.mp4"):
    print("[5/5] Uploading directly to YouTube...")
    creds = None
    video_id = None

    for attempt in range(4):
        media = None
        try:
            if os.path.exists("token.json"):
                creds = Credentials.from_authorized_user_file("token.json", SCOPES)
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file("client_secrets.json", SCOPES)
                    creds = flow.run_local_server(port=0)
                with open("token.json", "w") as t:
                    t.write(creds.to_json())

            youtube = build("youtube", "v3", credentials=creds)
            body = {
                "snippet": {
                    "title": f"{plan.title[:85]} #Shorts",
                    "description": f"{plan.description}\n\n#Shorts #Facts #{plan.category_badge.replace(' ', '')}",
                    "tags": plan.tags,
                    "categoryId": "27",
                },
                "status": {
                    "privacyStatus": "public",
                    "selfDeclaredMadeForKids": False,
                },
            }
            media = MediaFileUpload(file_path, chunksize=-1, resumable=False)
            req = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
            res = req.execute()
            video_id = res["id"]
            print(f"\nSUCCESS! Video is live at: https://youtube.com/shorts/{video_id}")
            break
        except Exception as e:
            err_str = str(e)
            if "quotaExceeded" in err_str or "uploadLimitExceeded" in err_str:
                print("\n[YOUTUBE DAILY LIMIT REACHED]")
                print(" -> Your rendered video is safely preserved at: C:\\YouTubeBot\\final_short.mp4")
                print(" -> Unlock higher daily limits in YouTube Studio -> Settings -> Channel -> Feature Eligibility.")
                print(" -> Next time you click your Desktop EXE after your limit resets, it will upload this video immediately!")
                return False
            print(f"   -> Network/Upload hiccup (attempt {attempt + 1}/4): {e}")
            print("   -> Retrying in 5 seconds...")
            time.sleep(5)
        finally:
            if media is not None:
                del media
            gc.collect()

    if not video_id:
        raise RuntimeError("Failed to upload after 4 network attempts.")

    # Only delete final_short.mp4 after a confirmed YouTube upload!
    time.sleep(1)
    for temp_file in [file_path, "voice.mp3", "last_plan.json"]:
        try:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        except OSError:
            pass
    return True


def run_single_cycle():
    # Smart Resume: If final_short.mp4 is already waiting from a previous daily limit, upload it first!
    if os.path.exists("final_short.mp4") and os.path.exists("last_plan.json"):
        print("\n[SMART RESUME] Found existing final_short.mp4 waiting for upload!")
        with open("last_plan.json", "r", encoding="utf-8") as f:
            plan = ShortPlan.model_validate_json(f.read())
        uploaded = upload_video(plan)
        if not uploaded:
            return
    else:
        plan = generate_plan()
        words_timeline, beat_durations = build_interactive_voiceover(plan)
        build_animated_video(plan, words_timeline, beat_durations)
        upload_video(plan)


if __name__ == "__main__":
    while True:
        try:
            run_single_cycle()
        except Exception as err:
            print(f"\n[Cycle Error]: {err}")
        if not RUN_24_7_LOOP:
            break
        wait_seconds = int(HOURS_BETWEEN_UPLOADS * 3600)
        print(f"\n[AUTOPILOT ACTIVE] Sleeping for {HOURS_BETWEEN_UPLOADS} hours before making the next video...")
        time.sleep(wait_seconds)
