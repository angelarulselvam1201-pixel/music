# music_app.py
import streamlit as st
import os
from datetime import datetime, timedelta
import time

# Try to use mutagen to get real mp3 duration; fall back if not installed
try:
    from mutagen.mp3 import MP3
    MUTAGEN_AVAILABLE = True
except Exception:
    MUTAGEN_AVAILABLE = False

st.set_page_config(page_title="Music App", layout="centered")

# ------------------ SETTINGS ------------------
MUSIC_FOLDER = "music"
ESTIMATED_SONG_LENGTH = 180  # seconds fallback if mutagen not available

# Ensure music folder exists (fixes FileNotFoundError)
if not os.path.exists(MUSIC_FOLDER):
    try:
        os.makedirs(MUSIC_FOLDER, exist_ok=True)
    except Exception as e:
        st.error(f"Unable to create music folder: {e}")
        st.stop()

# ------------------ Session state ------------------
if "play_count" not in st.session_state:
    st.session_state.play_count = {}  # {song: [datetime, ...]}

if "favorite_songs" not in st.session_state:
    st.session_state.favorite_songs = []

if "total_music_time" not in st.session_state:
    st.session_state.total_music_time = 0  # seconds (accurate when mutagen available)

if "durations" not in st.session_state:
    st.session_state.durations = {}  # cache durations {filename: seconds}

# ------------------ Helpers ------------------
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

def get_duration_seconds(path):
    """Return duration in seconds for mp3 using mutagen if available, else estimate."""
    if path in st.session_state.durations:
        return st.session_state.durations[path]
    full = os.path.join(MUSIC_FOLDER, path)
    if MUTAGEN_AVAILABLE:
        try:
            audio = MP3(full)
            dur = int(audio.info.length)
            st.session_state.durations[path] = dur
            return dur
        except Exception:
            pass
    # fallback
    st.session_state.durations[path] = ESTIMATED_SONG_LENGTH
    return ESTIMATED_SONG_LENGTH

def update_play_count(song):
    """Record a play timestamp, prune to 24 hours, update favorites if >=4 plays."""
    now = datetime.now()
    if song not in st.session_state.play_count:
        st.session_state.play_count[song] = []
    st.session_state.play_count[song].append(now)
    cutoff = now - timedelta(hours=24)
    st.session_state.play_count[song] = [t for t in st.session_state.play_count[song] if t > cutoff]
    if len(st.session_state.play_count[song]) >= 4 and song not in st.session_state.favorite_songs:
        st.session_state.favorite_songs.append(song)

# ------------------ UI ------------------
st.title("🎵 Music App — Robust Version")
st.write("Place `.mp3` files in the `music/` folder or use the uploader below. The app will:")
st.write("- Track total listening time (seconds).")
st.write("- Automatically add a song to Favorites if played 4+ times within 24 hours.")

# Show mutagen availability to user
if MUTAGEN_AVAILABLE:
    st.info("mutagen detected: song durations will be accurate.")
else:
    st.info("mutagen not installed: using estimated duration (180s). Install `mutagen` for accurate durations.")

# List current songs
songs = get_music_files()

# If folder empty, prompt to upload
if not songs:
    st.warning("No `.mp3` files found in the `music/` folder.")
    uploaded = st.file_uploader("Upload one or more MP3 files", type=["mp3"], accept_multiple_files=True)
    if uploaded:
        saved = save_uploaded_files(uploaded)
        st.success(f"Saved {len(saved)} file(s): " + ", ".join(saved))
        st.experimental_rerun()  # refresh to pick up saved files
    st.stop()

# If songs exist, show selection and play UI
selected_song = st.selectbox("Choose a song to play", songs)

col1, col2 = st.columns([3,1])
with col1:
    # Load bytes for playback
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

# Optional quick uploader (non-blocking) in sidebar
with st.sidebar.expander("Upload MP3s"):
    up_files = st.file_uploader("Select MP3 files", type=["mp3"], accept_multiple_files=True, key="sidebar_uploader")
    if st.button("Save uploaded files", key="save_uploads"):
        if up_files:
            saved = save_uploaded_files(up_files)
            st.success(f"Saved {len(saved)} file(s): " + ", ".join(saved))
            st.experimental_rerun()
        else:
            st.info("No files selected to save.")

# Handle play tracking
if play_btn:
    # update play-count timestamps & favorites
    update_play_count(selected_song)
    # add duration to total listening time
    dur = get_duration_seconds(selected_song)
    st.session_state.total_music_time += dur
    st.success(f"Recorded play for **{selected_song}** (+{dur} sec)")

# ------------------ Display Stats ------------------
st.subheader("📊 Music Stats")

total_seconds = st.session_state.total_music_time
h = total_seconds // 3600
m = (total_seconds % 3600) // 60
s = total_seconds % 60
st.metric("Total Listening Time", f"{h}h {m}m {s}s")

st.write("**Favorite Playlist (auto)** — songs played 4+ times within last 24 hours")
if st.session_state.favorite_songs:
    for sname in st.session_state.favorite_songs:
        st.markdown(f"- 🎶 **{sname}**")
else:
    st.info("No favorites yet. Play any song 4+ times within 24 hours to add it automatically.")

with st.expander("🔎 Play count log (last 24 hrs per song)"):
    # show readable timestamps
    pretty = {k: [t.strftime("%Y-%m-%d %H:%M:%S") for t in v] for k, v in st.session_state.play_count.items()}
    st.json(pretty)

# Option to remove a favorite
with st.expander("Manage Favorites"):
    if st.session_state.favorite_songs:
        rem = st.selectbox("Select favorite to remove", st.session_state.favorite_songs, key="fav_remove_select")
        if st.button("Remove from favorites"):
            st.session_state.favorite_songs = [x for x in st.session_state.favorite_songs if x != rem]
            st.success(f"Removed {rem} from favorites")
    else:
        st.write("No favorites to manage.")

# Option to delete uploaded music files (useful on dev environments)
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

st.caption("Tip: If you deploy on Streamlit Cloud, uploaded files will be stored only for the session/app instance — consider using external storage for persistence.")
