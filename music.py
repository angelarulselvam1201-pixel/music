/*
==========================================================
Musictooo — Flutter Mobile App (Single-file: lib/main.dart)
Royal Purple + Black theme, animated album art, auto-favorite,
total listening time tracking, persistent storage.

Before running:
1) Create a Flutter project:
   flutter create musictooo
   cd musictooo

2) Replace lib/main.dart with this file.

3) Add dependencies to pubspec.yaml (merge under existing sections):

dependencies:
  flutter:
    sdk: flutter
  cupertino_icons: ^1.0.5
  just_audio: ^0.9.45
  audio_session: ^0.1.6
  shared_preferences: ^2.0.15
  provider: ^6.0.5
  intl: ^0.18.0

flutter:
  uses-material-design: true
  assets:
    - assets/songs/song1.mp3
    - assets/songs/song2.mp3
    - assets/songs/song3.mp3
    - assets/art/song1.jpg
    - assets/art/song2.jpg
    - assets/art/song3.jpg

4) Place mp3 files in assets/songs/ and album art in assets/art/.
   Example names used in this file: song1.mp3, song2.mp3, song3.mp3
   and matching song1.jpg, song2.jpg, song3.jpg

5) Run:
   flutter pub get
   flutter run

==========================================================
*/

import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:just_audio/just_audio.dart';
import 'package:audio_session/audio_session.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';

void main() {
  runApp(const MusictoooApp());
}

/* ----------------------------- Models & Helpers ----------------------------- */

class Song {
  final String id;
  final String title;
  final String assetPath; // mp3 asset
  final String artPath; // album art asset

  const Song({
    required this.id,
    required this.title,
    required this.assetPath,
    required this.artPath,
  });
}

/* ----------------------------- App State ----------------------------- */

class MusicState extends ChangeNotifier {
  final List<Song> songs = const [
    Song(
      id: 'song1',
      title: 'Aurora Nights',
      assetPath: 'assets/songs/song1.mp3',
      artPath: 'assets/art/song1.jpg',
    ),
    Song(
      id: 'song2',
      title: 'Midnight Drift',
      assetPath: 'assets/songs/song2.mp3',
      artPath: 'assets/art/song2.jpg',
    ),
    Song(
      id: 'song3',
      title: 'Stellar Winds',
      assetPath: 'assets/songs/song3.mp3',
      artPath: 'assets/art/song3.jpg',
    ),
  ];

  final AudioPlayer player = AudioPlayer();
  int currentIndex = -1;
  bool isPlaying = false;
  Duration position = Duration.zero;
  Duration duration = Duration.zero;

  // persistence
  Map<String, List<DateTime>> playLog = {}; // songId -> timestamps
  List<String> favorites = [];
  int totalSeconds = 0;

  Timer? _pulseTimer;
  double visualPulse = 0.0; // 0..1 used by animation

  MusicState() {
    _init();
  }

  Future<void> _init() async {
    // Audio session recommended for mobile audio focus
    final session = await AudioSession.instance;
    await session.configure(const AudioSessionConfiguration.music());

    // Load persisted data
    await _loadState();

    // Setup listeners
    player.playerStateStream.listen((state) {
      final playing = state.playing;
      isPlaying = playing;
      notifyListeners();
      if (state.processingState == ProcessingState.completed) {
        _onTrackComplete();
      }
      if (isPlaying) {
        _startPulse();
      } else {
        _stopPulse();
      }
    });

    player.positionStream.listen((p) {
      position = p;
      notifyListeners();
    });

    player.durationStream.listen((d) {
      duration = d ?? Duration.zero;
      notifyListeners();
    });
  }

  Future<void> _loadState() async {
    final prefs = await SharedPreferences.getInstance();
    final rawLog = prefs.getString('play_log');
    if (rawLog != null) {
      try {
        final decoded = json.decode(rawLog) as Map<String, dynamic>;
        playLog = decoded.map((k, v) {
          final list = (v as List).map((s) => DateTime.parse(s as String)).toList();
          return MapEntry(k, list);
        });
      } catch (_) {
        playLog = {};
      }
    }
    favorites = prefs.getStringList('favorites') ?? [];
    totalSeconds = prefs.getInt('total_seconds') ?? 0;
    notifyListeners();
  }

  Future<void> _saveState() async {
    final prefs = await SharedPreferences.getInstance();
    final Map<String, List<String>> encoded = {};
    playLog.forEach((k, v) {
      encoded[k] = v.map((d) => d.toIso8601String()).toList();
    });
    await prefs.setString('play_log', json.encode(encoded));
    await prefs.setStringList('favorites', favorites);
    await prefs.setInt('total_seconds', totalSeconds);
  }

  Future<void> playIndex(int index) async {
    if (index < 0 || index >= songs.length) return;
    final song = songs[index];
    try {
      await player.setAsset(song.assetPath);
      await player.play();
      currentIndex = index;
      _recordPlay(song.id);
      notifyListeners();
    } catch (e) {
      // handle missing asset / playback error gracefully
      debugPrint('Playback error: $e');
    }
  }

  Future<void> pause() async {
    await player.pause();
    notifyListeners();
  }

  Future<void> seek(Duration at) async {
    await player.seek(at);
  }

  Future<void> stop() async {
    await player.stop();
    currentIndex = -1;
    position = Duration.zero;
    duration = Duration.zero;
    notifyListeners();
  }

  void _recordPlay(String songId) {
    final now = DateTime.now();
    playLog.putIfAbsent(songId, () => []);
    playLog[songId]!.add(now);
    // prune older than 24 hours
    final cutoff = now.subtract(const Duration(hours: 24));
    playLog[songId] = playLog[songId]!.where((t) => t.isAfter(cutoff)).toList();
    if (playLog[songId]!.length >= 4 && !favorites.contains(songId)) {
      favorites.add(songId);
    }
    _saveState();
    notifyListeners();
  }

  Future<void> _onTrackComplete() async {
    // add track duration to totalSeconds (fallback if unknown)
    final sec = duration.inSeconds > 0 ? duration.inSeconds : 180;
    totalSeconds += sec;
    await _saveState();
    notifyListeners();
  }

  String formatTotalTime() {
    final h = totalSeconds ~/ 3600;
    final m = (totalSeconds % 3600) ~/ 60;
    final s = totalSeconds % 60;
    if (h > 0) return '${h}h ${m}m ${s}s';
    if (m > 0) return '${m}m ${s}s';
    return '${s}s';
  }

  void removeFavorite(String id) {
    favorites.remove(id);
    _saveState();
    notifyListeners();
  }

  void resetAll() {
    playLog.clear();
    favorites.clear();
    totalSeconds = 0;
    _saveState();
    notifyListeners();
  }

  // Visual pulse controls (not real audio amplitude, but synced to play)
  void _startPulse() {
    _pulseTimer?.cancel();
    _pulseTimer = Timer.periodic(const Duration(milliseconds: 200), (_) {
      visualPulse = (visualPulse + 0.18) % 1.0;
      notifyListeners();
    });
  }

  void _stopPulse() {
    _pulseTimer?.cancel();
    visualPulse = 0.0;
    notifyListeners();
  }

  @override
  void dispose() {
    player.dispose();
    _pulseTimer?.cancel();
    super.dispose();
  }
}

/* ----------------------------- UI ----------------------------- */

class MusictoooApp extends StatelessWidget {
  const MusictoooApp({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (_) => MusicState(),
      child: MaterialApp(
        debugShowCheckedModeBanner: false,
        title: 'Musictooo',
        theme: ThemeData(
          brightness: Brightness.dark,
          scaffoldBackgroundColor: const Color(0xFF050006), // near black
          primaryColor: const Color(0xFF6A0DAD), // royal purple
          colorScheme: ColorScheme.dark(
            primary: const Color(0xFF6A0DAD),
            secondary: const Color(0xFF9B4CFF),
          ),
          textTheme: const TextTheme(
            headline6: TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
            bodyText2: TextStyle(color: Colors.white70),
          ),
        ),
        home: const HomeScreen(),
      ),
    );
  }
}

class HomeScreen extends StatelessWidget {
  const HomeScreen({Key? key}) : super(key: key);

  Widget _buildHeader(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 20, horizontal: 16),
      alignment: Alignment.center,
      child: ShaderMask(
        shaderCallback: (bounds) {
          return const LinearGradient(
            colors: [Color(0xFF8E2DE2), Color(0xFF6A0DAD)],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ).createShader(bounds);
        },
        child: const Text(
          'MUSICTOOO',
          style: TextStyle(
            fontSize: 36,
            fontWeight: FontWeight.w900,
            letterSpacing: 2.0,
            color: Colors.white,
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final state = Provider.of<MusicState>(context);
    return Scaffold(
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        title: _buildHeader(context),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => state.notifyListeners(),
            tooltip: 'Refresh',
            color: Colors.white70,
          ),
          PopupMenuButton<String>(
            color: const Color(0xFF0B0011),
            onSelected: (v) {
              if (v == 'reset') state.resetAll();
            },
            itemBuilder: (_) => [
              const PopupMenuItem(value: 'reset', child: Text('Reset Data')),
            ],
            icon: const Icon(Icons.more_vert, color: Colors.white70),
          ),
        ],
      ),
      body: Column(
        children: [
          // Top card: currently playing / big album art
          Expanded(
            flex: 6,
            child: GestureDetector(
              onTap: () {
                if (state.currentIndex >= 0) {
                  Navigator.of(context).push(MaterialPageRoute(builder: (_) => const PlayerScreen()));
                }
              },
              child: Container(
                margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                decoration: BoxDecoration(
                  color: const Color(0xFF070007),
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: const Color(0xFF4A148C).withOpacity(0.35)),
                  boxShadow: [
                    BoxShadow(
                      color: const Color(0xFF6A0DAD).withOpacity(0.08),
                      blurRadius: 30,
                      spreadRadius: 2,
                      offset: const Offset(0, 10),
                    ),
                  ],
                ),
                child: Center(
                  child: state.currentIndex >= 0
                      ? AlbumArtAnimated(song: state.songs[state.currentIndex])
                      : _NoTrackCard(),
                ),
              ),
            ),
          ),

          // middle: controls + progress
          Expanded(
            flex: 2,
            child: ControlArea(),
          ),

          // bottom: list and favorites
          Expanded(
            flex: 5,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              child: Column(
                children: [
                  _SectionTitle(title: 'Your Library'),
                  Expanded(child: SongList()),
                  const SizedBox(height: 8),
                  _SectionTitle(title: 'Your Hot Picks'),
                  FavoriteChips(),
                  const SizedBox(height: 8),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/* ----------------------------- Small UI Components ----------------------------- */

class _SectionTitle extends StatelessWidget {
  final String title;
  const _SectionTitle({Key? key, required this.title}) : super(key: key);
  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: Alignment.centerLeft,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 6, horizontal: 6),
        child: Text(
          title,
          style: TextStyle(color: Colors.white.withOpacity(0.9), fontWeight: FontWeight.w700),
        ),
      ),
    );
  }
}

class _NoTrackCard extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Column(mainAxisSize: MainAxisSize.min, children: [
      Icon(Icons.music_note, size: 80, color: Colors.white12),
      const SizedBox(height: 12),
      Text('No song playing', style: TextStyle(color: Colors.white54)),
      const SizedBox(height: 8),
      Text('Tap a track below to start', style: TextStyle(color: Colors.white24)),
    ]);
  }
}

/* ----------------------------- Album Art Animated Widget ----------------------------- */

class AlbumArtAnimated extends StatefulWidget {
  final Song song;
  const AlbumArtAnimated({Key? key, required this.song}) : super(key: key);

  @override
  State<AlbumArtAnimated> createState() => _AlbumArtAnimatedState();
}

class _AlbumArtAnimatedState extends State<AlbumArtAnimated> with SingleTickerProviderStateMixin {
  late AnimationController _rotationController;
  late Animation<double> _rotationAnim;
  @override
  void initState() {
    super.initState();
    _rotationController = AnimationController(vsync: this, duration: const Duration(seconds: 12));
    _rotationAnim = Tween<double>(begin: 0.0, end: 1.0).animate(CurvedAnimation(parent: _rotationController, curve: Curves.linear));
    _rotationController.repeat();
  }

  @override
  void didUpdateWidget(covariant AlbumArtAnimated oldWidget) {
    super.didUpdateWidget(oldWidget);
    // keep rotating continuously; pause/continue based on player state handled by parent pulse
  }

  @override
  void dispose() {
    _rotationController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final state = Provider.of<MusicState>(context);
    final pulse = state.visualPulse;
    // map pulse 0..1 to scale 0.98..1.06
    final scale = 0.98 + 0.08 * pulse;
    return Center(
      child: Stack(
        alignment: Alignment.center,
        children: [
          // blurred glowing ring behind art
          Container(
            width: 240,
            height: 240,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              gradient: RadialGradient(
                colors: [
                  const Color(0xFF6A0DAD).withOpacity(0.06),
                  const Color(0xFF9B4CFF).withOpacity(0.02),
                  Colors.transparent,
                ],
                stops: const [0.0, 0.45, 1.0],
              ),
            ),
          ),

          // rotating album art with slight scale pulse
          AnimatedScale(
            scale: scale,
            duration: const Duration(milliseconds: 220),
            child: RotationTransition(
              turns: _rotationAnim,
              child: ClipRRect(
                borderRadius: BorderRadius.circular(16),
                child: Container(
                  width: 200,
                  height: 200,
                  decoration: BoxDecoration(
                    boxShadow: [
                      BoxShadow(
                        color: const Color(0xFF6A0DAD).withOpacity(0.18),
                        blurRadius: 30,
                        spreadRadius: 2,
                      ),
                    ],
                  ),
                  child: Image.asset(widget.song.artPath, fit: BoxFit.cover, errorBuilder: (_, __, ___) {
                    return Container(
                      color: const Color(0xFF0A0011),
                      child: const Icon(Icons.album, size: 80, color: Colors.white12),
                    );
                  }),
                ),
              ),
            ),
          ),

          // subtle glowing ring overlay
          Positioned.fill(
            child: IgnorePointer(
              child: Center(
                child: Container(
                  width: 260,
                  height: 260,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    border: Border.all(color: const Color(0xFF6A0DAD).withOpacity(0.18), width: 2),
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/* ----------------------------- Song List ----------------------------- */

class SongList extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final state = Provider.of<MusicState>(context);
    return ListView.builder(
      itemCount: state.songs.length,
      itemBuilder: (context, i) {
        final song = state.songs[i];
        final isCurrent = (i == state.currentIndex);
        final plays = state.playLog[song.id]?.length ?? 0;
        final isFav = state.favorites.contains(song.id);
        return Card(
          color: const Color(0xFF070007),
          margin: const EdgeInsets.symmetric(vertical: 6, horizontal: 6),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12), side: BorderSide(color: const Color(0xFF4A148C).withOpacity(isCurrent ? 0.6 : 0.15))),
          child: ListTile(
            leading: ClipRRect(
              borderRadius: BorderRadius.circular(8),
              child: Image.asset(song.artPath, width: 52, height: 52, fit: BoxFit.cover, errorBuilder: (_, __, ___) {
                return Container(width: 52, height: 52, color: const Color(0xFF0A0011), child: const Icon(Icons.music_note, color: Colors.white12));
              }),
            ),
            title: Text(song.title, style: TextStyle(color: isCurrent ? const Color(0xFF9B4CFF) : Colors.white)),
            subtitle: Text('Plays (24h): $plays', style: const TextStyle(color: Colors.white54)),
            trailing: Row(mainAxisSize: MainAxisSize.min, children: [
              IconButton(
                icon: Icon(isFav ? Icons.favorite : Icons.favorite_border, color: isFav ? const Color(0xFF9B4CFF) : Colors.white70),
                onPressed: () {
                  if (isFav) {
                    state.removeFavorite(song.id);
                  } else {
                    state.favorites.add(song.id);
                    state._saveState();
                    state.notifyListeners();
                  }
                },
              ),
              IconButton(
                icon: Icon(isCurrent && state.isPlaying ? Icons.pause_circle_filled : Icons.play_circle_fill, size: 32, color: const Color(0xFF9B4CFF)),
                onPressed: () {
                  if (isCurrent) {
                    if (state.isPlaying) {
                      state.pause();
                    } else {
                      state.player.play();
                    }
                  } else {
                    state.playIndex(i);
                  }
                },
              ),
            ]),
          ),
        );
      },
    );
  }
}

/* ----------------------------- Control Area ----------------------------- */

class ControlArea extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final state = Provider.of<MusicState>(context);
    final current = (state.currentIndex >= 0) ? state.songs[state.currentIndex] : null;

    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 16),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFF050006),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFF4A148C).withOpacity(0.18)),
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          // now playing text
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Expanded(
                child: Text(
                  current?.title ?? 'No track selected',
                  style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700, color: Colors.white),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              Text(state.formatTotalTime(), style: const TextStyle(color: Colors.white70)),
            ],
          ),
          const SizedBox(height: 12),

          // progress slider
          Row(
            children: [
              Text(_formatDuration(state.position), style: const TextStyle(color: Colors.white54, fontSize: 12)),
              Expanded(
                child: SliderTheme(
                  data: SliderThemeData(
                    trackHeight: 4,
                    thumbColor: const Color(0xFF9B4CFF),
                    activeTrackColor: const Color(0xFF6A0DAD),
                    inactiveTrackColor: Colors.white12,
                    overlayColor: const Color(0xFF9B4CFF).withOpacity(0.2),
                  ),
                  child: Slider(
                    value: state.position.inMilliseconds.toDouble().clamp(0.0, (state.duration.inMilliseconds.toDouble() <= 0 ? 1.0 : state.duration.inMilliseconds.toDouble())),
                    max: (state.duration.inMilliseconds.toDouble() <= 0 ? 1.0 : state.duration.inMilliseconds.toDouble()),
                    onChanged: (val) {
                      state.seek(Duration(milliseconds: val.toInt()));
                    },
                  ),
                ),
              ),
              Text(_formatDuration(state.duration), style: const TextStyle(color: Colors.white54, fontSize: 12)),
            ],
          ),

          // control buttons
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              IconButton(
                icon: const Icon(Icons.skip_previous, size: 32, color: Colors.white70),
                onPressed: () {
                  final idx = state.currentIndex;
                  if (idx > 0) state.playIndex(idx - 1);
                },
              ),
              const SizedBox(width: 8),
              ElevatedButton(
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF9B4CFF),
                  shape: const CircleBorder(),
                  padding: const EdgeInsets.all(12),
                ),
                child: Icon(state.isPlaying ? Icons.pause : Icons.play_arrow, size: 36, color: Colors.black),
                onPressed: () {
                  if (state.currentIndex >= 0) {
                    if (state.isPlaying) {
                      state.pause();
                    } else {
                      if (state.player.playing) {
                        state.player.play();
                      } else {
                        // if not loaded, play current index or first
                        if (state.currentIndex >= 0) {
                          state.playIndex(state.currentIndex);
                        } else {
                          state.playIndex(0);
                        }
                      }
                    }
                  } else {
                    state.playIndex(0);
                  }
                },
              ),
              const SizedBox(width: 8),
              IconButton(
                icon: const Icon(Icons.skip_next, size: 32, color: Colors.white70),
                onPressed: () {
                  final idx = state.currentIndex;
                  if (idx < state.songs.length - 1) state.playIndex(idx + 1);
                },
              ),
            ],
          ),
        ],
      ),
    );
  }

  String _formatDuration(Duration d) {
    final mm = d.inMinutes.remainder(60).toString().padLeft(2, '0');
    final ss = d.inSeconds.remainder(60).toString().padLeft(2, '0');
    return '${mm}:${ss}';
  }
}

/* ----------------------------- Favorite Chips ----------------------------- */

class FavoriteChips extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final state = Provider.of<MusicState>(context);
    if (state.favorites.isEmpty) {
      return Padding(
        padding: const EdgeInsets.symmetric(horizontal: 6),
        child: Text('No hot picks yet — play a track 4+ times in 24 hours to auto-add.',
            style: TextStyle(color: Colors.white54)),
      );
    }
    return SizedBox(
      height: 48,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: state.favorites.length,
        separatorBuilder: (_, __) => const SizedBox(width: 8),
        itemBuilder: (context, i) {
          final id = state.favorites[i];
          final song = state.songs.firstWhere((s) => s.id == id, orElse: () => Song(id: id, title: id, assetPath: '', artPath: ''));
          return Padding(
            padding: const EdgeInsets.symmetric(horizontal: 6),
            child: InputChip(
              label: Text(song.title, style: const TextStyle(color: Colors.white)),
              avatar: const Icon(Icons.whatshot, color: Colors.amber),
              backgroundColor: const Color(0xFF1A001D),
              onDeleted: () => state.removeFavorite(id),
              deleteIconColor: Colors.white70,
            ),
          );
        },
      ),
    );
  }
}

/* ----------------------------- Player Screen (Full) ----------------------------- */

class PlayerScreen extends StatelessWidget {
  const PlayerScreen({Key? key}) : super(key: key);

  Widget _buildVisualizer(BuildContext context) {
    final state = Provider.of<MusicState>(context);
    final pulse = state.visualPulse;
    // create 12 bars with staggered heights derived from pulse
    return SizedBox(
      height: 80,
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: List.generate(12, (i) {
          final t = (pulse + i * 0.08) % 1.0;
          final height = 10 + (t * 1.0) * 56; // 10..66
          final color = Color.lerp(const Color(0xFF6A0DAD), const Color(0xFF9B4CFF), i / 12)!;
          return AnimatedContainer(
            duration: const Duration(milliseconds: 180),
            margin: const EdgeInsets.symmetric(horizontal: 3),
            width: 6,
            height: height,
            decoration: BoxDecoration(
              color: color,
              borderRadius: BorderRadius.circular(3),
              boxShadow: [BoxShadow(color: color.withOpacity(0.3), blurRadius: 6, spreadRadius: 1)],
            ),
          );
        }),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final state = Provider.of<MusicState>(context);
    final song = (state.currentIndex >= 0) ? state.songs[state.currentIndex] : null;

    return Scaffold(
      appBar: AppBar(
        title: Text(song?.title ?? 'Now Playing'),
        backgroundColor: Colors.transparent,
        elevation: 0,
      ),
      body: Column(
        children: [
          const SizedBox(height: 20),
          if (song != null)
            Expanded(
              child: Center(
                child: AlbumArtAnimated(song: song),
              ),
            ),
          const SizedBox(height: 10),
          _buildTitleArea(state),
          const SizedBox(height: 8),
          _buildPlaybackControls(state),
          const SizedBox(height: 20),
          _buildVisualizer(context),
          const SizedBox(height: 24),
        ],
      ),
    );
  }

  Widget _buildTitleArea(MusicState state) {
    final song = (state.currentIndex >= 0) ? state.songs[state.currentIndex] : null;
    return Column(
      children: [
        Text(song?.title ?? '', style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
        const SizedBox(height: 6),
        Text(state.position.inSeconds > 0 ? '${_formatDuration(state.position)} / ${_formatDuration(state.duration)}' : '00:00 / 00:00',
            style: const TextStyle(color: Colors.white54)),
      ],
    );
  }

  Widget _buildPlaybackControls(MusicState state) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        IconButton(
          icon: const Icon(Icons.skip_previous, size: 36, color: Colors.white70),
          onPressed: () {
            final idx = state.currentIndex;
            if (idx > 0) state.playIndex(idx - 1);
          },
        ),
        const SizedBox(width: 8),
        ElevatedButton(
          style: ElevatedButton.styleFrom(
            backgroundColor: const Color(0xFF9B4CFF),
            shape: const CircleBorder(),
            padding: const EdgeInsets.all(14),
          ),
          child: Icon(state.isPlaying ? Icons.pause : Icons.play_arrow, size: 36, color: Colors.black),
          onPressed: () {
            if (state.currentIndex >= 0) {
              if (state.isPlaying) {
                state.pause();
              } else {
                state.player.play();
              }
            }
          },
        ),
        const SizedBox(width: 8),
        IconButton(
          icon: const Icon(Icons.skip_next, size: 36, color: Colors.white70),
          onPressed: () {
            final idx = state.currentIndex;
            if (idx < state.songs.length - 1) state.playIndex(idx + 1);
          },
        ),
      ],
    );
  }

  String _formatDuration(Duration d) {
    final mm = d.inMinutes.remainder(60).toString().padLeft(2, '0');
    final ss = d.inSeconds.remainder(60).toString().padLeft(2, '0');
    return '$mm:$ss';
  }
}
