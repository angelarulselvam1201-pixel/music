import streamlit as st
import os
import time
import json
from datetime import datetime, timedelta

st.set_page_config(page_title="Music App", layout="centered")

# ------------------ INITIAL SETUP ------------------
if "play_count" not in st.session_state:
    st.session_state.play_count = {}  # {song: [timestamps]}
if "favorite_songs" not in st.session_state:
    st.session_state.favorite_songs = []
if "total_music_time" not in st.session_state:
    st.session_state.total_music_time = 0  # seconds

MUSIC_FOLDER = "music"

st.title("🎵 Music Streaming App")
st.write("Automatic Favourite Playlist → **If a song is played 4+ times in 24 hours**")


# ------------------ LOAD MUSIC ------------------
def get_music_files():
    return [f for f in os.listdir(MUSIC_FOLDER) if f.endswith(".mp3")]


songs = get_music_files()

if not songs:
    st.error("No music files found! Please add .mp3 files in the **music/** folder.")
    st.stop()


# ------------------ SELECT MUSIC ------------------
selected_song = st.selectbox("Choose a song to play:", songs)
song_path = os.path.join(MUSIC_FOLDER, selected_song)

# ------------------ AUDIO PLAYER ------------------
audio_file = open(song_path, "rb")
audio_bytes = audio_file.read()

st.audio(audio_bytes, format="audio/mp3")

play_btn = st.button("▶️ Count as Played")

# ------------------ HANDLE PLAY COUNT ------------------
def update_play_count(song):
    now = datetime.now()

    # Add timestamp to play count list
    if song not in st.session_state.play_count:
        st.session_state.play_count[song] = []

    st.session_state.play_count[song].append(now)

    # Remove timestamps older than 24 hours
    cutoff = now - timedelta(hours=24)
    st.session_state.play_count[song] = [
        t for t in st.session_state.play_count[song] if t > cutoff
    ]

    # Check if played 4+ times → add to favorites
    if len(st.session_state.play_count[song]) >= 4:
        if song not in st.session_state.favorite_songs:
            st.session_state.favorite_songs.append(song)

# ------------------ TOTAL LISTENING TIME (Approximation) ------------------
# Assume average song length = 3 minutes (180 sec)
# You can adjust with metadata reading if needed.

ESTIMATED_SONG_LENGTH = 180  # seconds


if play_btn:
    update_play_count(selected_song)

    # Update total listening time
    st.session_state.total_music_time += ESTIMATED_SONG_LENGTH

    st.success(f"🎧 Played: {selected_song}")


# ------------------ DISPLAY STATS ------------------
st.subheader("📊 Music Stats")

total_min = st.session_state.total_music_time // 60
total_sec = st.session_state.total_music_time % 60

st.metric("⏱ Total Music Listening Time", f"{total_min} min {total_sec} sec")


# ------------------ FAVORITE PLAYLIST ------------------
st.subheader("⭐ Auto Favorite Playlist (last 24 hrs)")

if st.session_state.favorite_songs:
    st.write("Songs added automatically after 4+ plays:")
    for s in st.session_state.favorite_songs:
        st.markdown(f"- 🎶 **{s}**")
else:
    st.info("No favorite songs yet. Play a song 4 times within 24 hours!")


# ------------------ PLAY COUNT DEBUG (optional) ------------------
with st.expander("🔎 Debug — Play Count Log"):
    st.json({k: [str(t) for t in v] for k, v in st.session_state.play_count.items()})
