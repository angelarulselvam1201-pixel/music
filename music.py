import streamlit as st
from datetime import datetime, timedelta
from random import randint
import time

# ---------------------------
# APP CONFIG
# ---------------------------
st.set_page_config(
    page_title="Musictooo",
    layout="centered",
    initial_sidebar_state="expanded",
)

# Dark Theme CSS
st.markdown(
    """
    <style>
    .css-18e3th9 {background-color:#0B031A;}
    .stButton>button {background-color:#6A0DAD;color:white;}
    .stSlider>div>div>div>div{color:#9B4BFF;}
    .stMarkdown p{color:white;}
    .stText{color:white;}
    .stProgress>div>div>div>div{background-color:#9B4BFF;}
    </style>
    """,
    unsafe_allow_html=True
)

# ---------------------------
# MUSIC DATA
# ---------------------------
songs = [
    {"title": "Dream Wave", "file": "song1.mp3", "art": "album1.jpg", "play_log": []},
    {"title": "Purple Skies", "file": "song2.mp3", "art": "album2.jpg", "play_log": []},
    {"title": "Midnight Echo", "file": "song3.mp3", "art": "album3.jpg", "play_log": []},
]

total_seconds = 0

# ---------------------------
# SIDEBAR
# ---------------------------
st.sidebar.title("Musictooo Player")
st.sidebar.markdown("Royal Purple + Dark Theme")

selected_song_index = st.sidebar.radio(
    "Select a song", range(len(songs)), format_func=lambda x: songs[x]["title"]
)

play_button = st.sidebar.button("Play / Pause")

# ---------------------------
# FUNCTIONS
# ---------------------------
def record_play(song):
    now = datetime.now()
    song["play_log"].append(now)
    cutoff = now - timedelta(hours=24)
    song["play_log"] = [t for t in song["play_log"] if t > cutoff]

def get_favorites():
    return [s for s in songs if len(s["play_log"]) >= 4]

def format_time(seconds):
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h}h {m}m {s}s"
    elif m > 0:
        return f"{m}m {s}s"
    return f"{s}s"

# ---------------------------
# MAIN
# ---------------------------
st.markdown("<h1 style='color:#9B4BFF;text-align:center;'>MUSICTOOO</h1>", unsafe_allow_html=True)

song = songs[selected_song_index]
st.image(song["art"], width=250, use_column_width=False)

st.markdown(f"### {song['title']}")

# Animate album art (fake rotation using st.image updates)
album_art_placeholder = st.empty()
for i in range(1):  # Only 1 cycle to avoid long loop; Streamlit animation is limited
    album_art_placeholder.image(song["art"], width=250)

if play_button:
    record_play(song)
    total_seconds += 180  # Simulate song duration for example
    st.success(f"Playing '{song['title']}' 🎵")
    st.progress(randint(1, 100))

st.markdown(f"**Total Listening Time:** {format_time(total_seconds)}")

# Favorites
favorites = get_favorites()
st.markdown("### Favorites")
if favorites:
    for fav in favorites:
        st.markdown(f"- {fav['title']} (Plays in 24h: {len(fav['play_log'])})")
else:
    st.markdown("_No favorites yet. Play a song 4+ times in 24h to auto-add._")

# Song list
st.markdown("### All Songs")
for s in songs:
    st.markdown(f"- {s['title']} (Plays in 24h: {len(s['play_log'])})")
