import streamlit as st
import os
from datetime import datetime, timedelta

# Optional audio duration metadata
try:
    from mutagen.mp3 import MP3
    MUTAGEN_AVAILABLE = True
except:
    MUTAGEN_AVAILABLE = False

# --------------------------- PAGE CONFIG ---------------------------
st.set_page_config(page_title="MUSICTOOO", page_icon="🎧", layout="centered")

# --------------------------- CUSTOM CSS (ANIMATIONS) ---------------------------
st.markdown("""
<style>

body {
    background-color: #000000;
}

/* Spotify Style Header */
.title {
    font-size: 55px;
    font-weight: 800;
    text-align: center;
    background: linear-gradient(90deg, #1db954, #1ed760, #1db954);
    -webkit-background-clip: text;
    color: transparent;
    animation: glow 2s infinite alternate;
}

@keyframes glow {
    from { text-shadow: 0 0 10px #1db954; }
    to { text-shadow: 0 0 25px #1ed760; }
}

/* Song Card Animated */
.song-card {
    background: rgba(20,20,20,0.8);
    border-radius: 20px;
    padding: 25px;
    text-align: center;
    margin-top: 25px;
    transition: all 0.4s ease;
    border: 1px solid #1db954;
}

.song-card:hover {
    transform: scale(1.04);
    box-shadow: 0px 4px 25px #1db954;
}

/* Animated Equalizer Bars */
.equalizer {
    display: flex;
    justify-content: center;
    margin-top: 10px;
}

.bar {
    width: 6px;
    height: 20px;
    background: #1db954;
    margin: 0 3px;
    animation: bounce 1s infinite ease-in-out;
}

.bar:nth-child(1) { animation-delay: 0s; }
.bar:nth-child(2) { animation-delay: 0.2s; }
.bar:nth-child(3) { animation-delay: 0.4s; }
.bar:nth-child(4) { animation-delay: 0.2s; }
.bar:nth-child(5) { animation-delay: 0s; }

@keyframes bounce {
    0% { height: 10px; }
    50% { height: 35px; }
    100% { height: 10px; }
}

/* Stylish Buttons */
button {
    background-color: #1db954 !important;
    color: black !important;
    border-radius: 30px !important;
    font-weight: bold !important;
}

/* Playlist Tags */
.favorite-tag {
    color: #1db954;
    font-weight: bold;
}

</style>
""", unsafe_allow_html=True)

# --------------------------- INITIAL SETUP ---------------------------
MUSIC_FOLDER = "music"

if not os.path.exists(MUSIC_FOLDER):
    os.makedirs(MUSIC_FOLDER, exist_ok=True)

if "play_count" not in st.session_state:
    st.session_state.play_count = {}

if "favorite_songs" not in st.session_state:
    st.session_state.favorite_songs = []

if "total_music_time" not in st.session_state:
    st.session_state.total_music_time = 0

if "durations" not in st.session_state:
    st.session_state.durations = {}

# --------------------------- HELPERS ---------------------------

def get_music_files():
    return sorted([f for f in os.listdir(MUSIC_FOLDER) if f.lower().endswith(".mp3")])

def save_uploaded_files(uploaded_files):
    saved = []
    for up in uploaded_files:
        fname = up.name
        base, ext = os.path.splitext(fname)
        candidate = fname
        i = 1
        while os.path.exists(os.path.join(MUSIC_FOLDER, candidate)):
            candidate = f"{base}_{i}{ext}"
            i += 1
        path = os.path.join(MUSIC_FOLDER, candidate)
        with open(path, "wb") as f:
            f.write(up.read())
        saved.append(candidate)
    return saved

def get_duration(filename):
    if filename in st.session_state.durations:
        return st.session_state.durations[filename]

    path = os.path.join(MUSIC_FOLDER, filename)
    if MUTAGEN_AVAILABLE:
        try:
            audio = MP3(path)
            sec = int(audio.info.length)
            st.session_state.durations[filename] = sec
            return sec
        except:
            pass

    st.session_state.durations[filename] = 180
    return 180

def update_play_count(song):
    now = datetime.now()
    if song not in st.session_state.play_count:
        st.session_state.play_count[song] = []
    st.session_state.play_count[song].append(now)

    cutoff = now - timedelta(hours=24)
    st.session_state.play_count[song] = [
        t for t in st.session_state.play_count[song] if t > cutoff
    ]

    if len(st.session_state.play_count[song]) >= 4:
        if song not in st.session_state.favorite_songs:
            st.session_state.favorite_songs.append(song)

# --------------------------- UI ---------------------------

st.markdown("<div class='title'>🎧 MUSICTOOO</div>", unsafe_allow_html=True)
st.write("A modern, animated Spotify-style music player with auto-favorite system.")

songs = get_music_files()

# Upload if no songs exist
if not songs:
    st.warning("No MP3 files found! Upload songs below.")
    uploaded = st.file_uploader("Upload MP3 files", type=["mp3"], accept_multiple_files=True)
    if uploaded:
        saved = save_uploaded_files(uploaded)
        st.success("Uploaded: " + ", ".join(saved))
        st.experimental_rerun()
    st.stop()

# Song selection
selected = st.selectbox("Select Song", songs)

# Song Card Visual
st.markdown(f"""
<div class="song-card">
    <h2 style="color:white;">🎵 {selected}</h2>

    <div class="equalizer">
        <div class="bar"></div>
        <div class="bar"></div>
        <div class="bar"></div>
        <div class="bar"></div>
        <div class="bar"></div>
    </div>
</div>
""", unsafe_allow_html=True)

# Audio Playback
path = os.path.join(MUSIC_FOLDER, selected)
with open(path, "rb") as f:
    st.audio(f.read(), format="audio/mp3")

if st.button("▶️ Count as Play"):
    update_play_count(selected)
    duration = get_duration(selected)
    st.session_state.total_music_time += duration
    st.success(f"Played {selected}")

# --------------------------- STATS ---------------------------

st.subheader("📊 Total Listening Time")

total = st.session_state.total_music_time
hrs = total // 3600
mins = (total % 3600) // 60
secs = total % 60

st.metric("Time", f"{hrs}h {mins}m {secs}s")

# --------------------------- FAVORITE PLAYLIST ---------------------------

st.subheader("⭐ Favorite Playlist")

if st.session_state.favorite_songs:
    for s in st.session_state.favorite_songs:
        st.markdown(f"<div class='favorite-tag'>🎶 {s}</div>", unsafe_allow_html=True)
else:
    st.info("No favorites yet — play a song 4+ times in 24 hours.")

# --------------------------- DEBUG ---------------------------

with st.expander("Play Count Debug"):
    st.json({k: [str(t) for t in v] for k, v in st.session_state.play_count.items()})
