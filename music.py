# music.py
import streamlit as st
import os
from datetime import datetime, timedelta

# optional: use mutagen to get exact mp3 duration if available
try:
    from mutagen.mp3 import MP3
    MUTAGEN_AVAILABLE = True
except Exception:
    MUTAGEN_AVAILABLE = False

st.set_page_config(page_title="Music App", layout="centered")

# ---------------- Settings ----------------
MUSIC_FOLDER = "music"
ESTIMATED_SONG_LENGTH = 180  # seconds fallback if mutagen not available

# Ensure music folder exists
if not os.path.exists(MUSIC_FOLDER):
    try:
        os.makedirs(MUSIC_FOLDER, exist_ok=True)
    except Exception as e:
        st.error(f"Unable to create music folder: {e}")
        st.stop()

# ---------------- Session State ----------------
if "play_count" not in st.session_state:
    st.session_state.play_count = {}  # {song: [datetime, ...]}

if "favorite_songs" not in st.session_state:
    st.session_state.favorite_songs = []

if "total_music_time" not in st.session_state:
    st.session_state.total_music_time = 0  # seconds

if "durations" not in st.session_state:
    st.session_state.durations = {}

# ---------------- Helpers ----------------
def get_music_files():
    """Return list of mp3 files in MUSIC_FOLDER sorted alphabetically."""
    try:
        return sorted([f for f in os.listdir(MUSIC_FOLDER) if f.lower().endswith(".mp3")])
    except FileNotFoundError:
        return []

def save_uploaded_files(uploaded_files):
    """Save uploaded files into MUSIC_FOLDER. Avoid overwrite by adding index if needed."""
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
            f.write(up.getbuffer())
        saved.append(candidate)
    return saved

def get_duration_seconds(filename):
    """Return duration in seconds for mp3 using mutagen if available, else estimate."""
    if filename in st.session_state.durations:
        return st.session_state.durations[filename]
    full = os.path.join(MUSIC_FOLDER, filename)
    if MUTAGEN_AVAILABLE:
        try:
            audio = MP3(full)
            dur = int(audio.info.length)
            st.session_state.durations[filename] = dur
            return dur
        except Exception:
            pass
    st.session_state.durations[filename] = ESTIMATED_SONG_LENGTH
    return ESTIMATED_SONG_LENGTH

def update_play_count(song):
    """Record a play timestamp, prune to 24 hours, update favorites if >=4 plays."""
    now = datetime.now()
    if song not in st.session_state.play_count:
        st.session_state.play_count[song] = []
    st.session_state.play_count[song].append(now)
    cutoff = now - timedelta(hours=24)
    st.session_state.play_count[song] = [
        t for t in st.session_state.play_count[song] if t > cutoff
    ]
    if len(st.session_state.play_count[song]) >= 4 and song not in st.session_state.favorite_songs:
        st.session_state.favorite_songs.append(song)

# ---------------- UI ----------------
st.title("🎵 Music App — Fixed & Robust")
st.write("Place `.mp3` files inside the `music/` folder or upload them below. Features:")
st.write("- Tracks total listening time (by approximating from file duration).")
st.write("- Auto-favorite a song if played 4+ times within 24 hours.")

if MUTAGEN_AVAILABLE:
    st.info("mutagen detected: durations will be accurate.")
else:
    st.info("mutagen not installed: using estimated duration (180s). Install `mutagen` for exact durations.")

# List songs
songs = get_music_files()

# Upload UI when no songs exist
if not songs:
    st.warning("No `.mp3` files found in the `music/` folder.")
    uploaded = st.file_uploader("Upload one or more MP3 files", type=["mp3"], accept_multiple_files=True)
    if uploaded:
        saved = save_uploaded_files(uploaded)
        st.success(f"Saved {len(saved)} file(s): " + ", ".join(saved))
        st.experimental_rerun()
    st.stop()

# Show selection and playback controls
selected_song = st.selectbox("Choose a song to play", songs)

col1, col2 = st.columns([3,1])
with col1:
    song_path = os.path.join(MUSIC_FOLDER, selected_song)
    try:
        with open(song_path, "rb") as f:
            audio_bytes = f.read()
        st.audio(audio_bytes, format="audio/mp3")
    except Exception as e:
        st.error(f"Unable to read {selected_song}: {e}")

with col2:
    duration = get_duration_seconds(selected_song)
    mins = duration // 60
    secs = duration % 60
    st.metric("Duration", f"{mins}m {secs}s")

play_btn = st.button("▶️ Count as Played")

# Sidebar uploader for convenience
with st.sidebar.expander("Upload MP3s"):
    up_files = st.file_uploader("Select MP3 files", type=["mp3"], accept_multiple_files=True, key="sidebar_uploader")
    if st.button("Save uploaded files", key="save_uploads"):
        if up_files:
            saved = save_uploaded_files(up_files)
            st.success(f"Saved {len(saved)} file(s): " + ", ".join(saved))
            st.experimental_rerun()
        else:
            st.info("No files selected to save.")

# Play action handling
if play_btn:
    update_play_count(selected_song)
    dur = get_duration_seconds(selected_song)
    st.session_state.total_music_time += dur
    st.success(f"Recorded play for **{selected_song}** (+{dur} sec)")

# Stats
st.subheader("📊 Music Stats")
total_seconds = st.session_state.total_music_time
hours = total_seconds // 3600
minutes = (total_seconds % 3600) // 60
seconds = total_seconds % 60
st.metric("Total Listening Time", f"{hours}h {minutes}m {seconds}s")

st.write("**Favorite Playlist (auto)** — songs played 4+ times within last 24 hours")
if st.session_state.favorite_songs:
    for sname in st.session_state.favorite_songs:
        st.markdown(f"- 🎶 **{sname}**")
else:
    st.info("No favorites yet. Play any song 4+ times within 24 hours to add it automatically.")

with st.expander("🔎 Play count log (last 24 hrs per song)"):
    pretty = {k: [t.strftime("%Y-%m-%d %H:%M:%S") for t in v] for k, v in st.session_state.play_count.items()}
    st.json(pretty)

# Manage Favorites
with st.expander("Manage Favorites"):
    if st.session_state.favorite_songs:
        rem = st.selectbox("Select favorite to remove", st.session_state.favorite_songs, key="fav_remove_select")
        if st.button("Remove from favorites"):
            st.session_state.favorite_songs = [x for x in st.session_state.favorite_songs if x != rem]
            st.success(f"Removed {rem} from favorites")
    else:
        st.write("No favorites to manage.")

# File management
with st.expander("⚠️ Manage Files"):
    st.write("Files in the `music/` folder:")
    for f in songs:
        st.write(f"- {f}")
    del_name = st.text_input("Enter exact filename to delete (dangerous)", key="del_input")
    if st.button("Delete file"):
        if del_name and del_name in songs:
            try:
                os.remove(os.path.join(MUSIC_FOLDER, del_name))
                st.success(f"Deleted {del_name}")
                st.experimental_rerun()
            except Exception as e:
                st.error(f"Could not delete: {e}")
        else:
            st.error("Filename missing or not found in folder.")

st.caption("Note: On cloud platforms (Streamlit Cloud) uploaded files may not be persistent; use external storage for permanent hosting.")
