import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:just_audio/just_audio.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:intl/intl.dart';

void main() {
  runApp(MyApp());
}

class SongItem {
  final String id; // unique id (use asset path)
  final String title;
  final String assetPath;

  SongItem({required this.id, required this.title, required this.assetPath});
}

class MyApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Advanced Music App',
      theme: ThemeData(
        primarySwatch: Colors.indigo,
      ),
      home: MusicHomePage(),
    );
  }
}

class MusicHomePage extends StatefulWidget {
  @override
  State<MusicHomePage> createState() => _MusicHomePageState();
}

class _MusicHomePageState extends State<MusicHomePage> {
  // Built-in songs (update titles & asset paths to match your assets)
  final List<SongItem> songs = [
    SongItem(id: 'song1', title: 'Sunny Breeze', assetPath: 'assets/songs/song1.mp3'),
    SongItem(id: 'song2', title: 'Evening Chill', assetPath: 'assets/songs/song2.mp3'),
    SongItem(id: 'song3', title: 'Road Trip', assetPath: 'assets/songs/song3.mp3'),
  ];

  final AudioPlayer _player = AudioPlayer();
  int _currentIndex = -1;
  bool _isPlaying = false;
  Duration _currentPosition = Duration.zero;
  Duration _currentDuration = Duration.zero;

  // Persistent data keys
  static const String KEY_PLAY_LOG = 'play_log'; // map songId -> list of ISO timestamps
  static const String KEY_FAVORITES = 'favorites'; // list of songId
  static const String KEY_TOTAL_SECONDS = 'total_seconds'; // int

  Map<String, List<DateTime>> playLog = {}; // in-memory
  List<String> favorites = [];
  int totalSeconds = 0;

  Timer? _positionTimer;
  StreamSubscription<Duration>? _posSub;
  StreamSubscription<PlayerState>? _playerStateSub;

  @override
  void initState() {
    super.initState();
    _loadPersistentState();
    _player.durationStream.listen((d) {
      if (d != null) {
        setState(() => _currentDuration = d);
      }
    });
    _posSub = _player.positionStream.listen((p) {
      setState(() => _currentPosition = p);
    });
    _playerStateSub = _player.playerStateStream.listen((state) {
      final playing = state.playing;
      setState(() => _isPlaying = playing);
      // when playback completes, handle total time addition (if we haven't yet)
      if (state.processingState == ProcessingState.completed) {
        _onSongComplete();
      }
    });
  }

  @override
  void dispose() {
    _player.dispose();
    _posSub?.cancel();
    _playerStateSub?.cancel();
    _positionTimer?.cancel();
    super.dispose();
  }

  Future<void> _loadPersistentState() async {
    final prefs = await SharedPreferences.getInstance();
    // load play log
    final playLogRaw = prefs.getString(KEY_PLAY_LOG);
    if (playLogRaw != null) {
      final Map<String, dynamic> decoded = json.decode(playLogRaw);
      playLog = decoded.map((k, v) {
        final List list = v as List;
        final times = list.map<DateTime>((x) => DateTime.parse(x as String)).toList();
        return MapEntry(k, times);
      });
    } else {
      playLog = {};
    }
    // favorites
    favorites = prefs.getStringList(KEY_FAVORITES) ?? [];
    // total seconds
    totalSeconds = prefs.getInt(KEY_TOTAL_SECONDS) ?? 0;
    setState(() {});
  }

  Future<void> _savePersistentState() async {
    final prefs = await SharedPreferences.getInstance();
    // save play log as map of lists ISO strings
    final Map<String, List<String>> toSave = {};
    playLog.forEach((k, v) {
      toSave[k] = v.map((d) => d.toIso8601String()).toList();
    });
    prefs.setString(KEY_PLAY_LOG, json.encode(toSave));
    prefs.setStringList(KEY_FAVORITES, favorites);
    prefs.setInt(KEY_TOTAL_SECONDS, totalSeconds);
  }

  Future<void> _playSong(int index) async {
    try {
      final song = songs[index];
      // load asset
      await _player.setAsset(song.assetPath);
      await _player.play();
      _currentIndex = index;

      // record a play (timestamp) and check favorite logic
      _recordPlayAndMaybeFavorite(song.id);

      // attempt to get duration (just_audio sets durationStream)
      // if duration is available we will add to totalSeconds after playback completes
      setState(() {});
    } catch (e) {
      // asset missing or other error
      debugPrint('Playback error: $e');
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text('Unable to play song: ${e.toString()}'),
      ));
    }
  }

  Future<void> _pauseSong() async {
    await _player.pause();
  }

  Future<void> _stopSong() async {
    await _player.stop();
    setState(() {
      _currentIndex = -1;
      _currentPosition = Duration.zero;
      _currentDuration = Duration.zero;
    });
  }

  void _recordPlayAndMaybeFavorite(String songId) {
    final now = DateTime.now();

    // append timestamp
    if (!playLog.containsKey(songId)) playLog[songId] = [];
    playLog[songId]!.add(now);

    // prune timestamps older than 24 hours
    final cutoff = now.subtract(Duration(hours: 24));
    playLog[songId] = playLog[songId]!.where((t) => t.isAfter(cutoff)).toList();

    // if plays >= 4 in last 24 hours => add to favorites
    if (playLog[songId]!.length >= 4 && !favorites.contains(songId)) {
      favorites.add(songId);
      // notify user
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text('Added to Favorites: ${_getTitleById(songId)}'),
        backgroundColor: Colors.green,
      ));
    }

    // persist
    _savePersistentState();
    setState(() {});
  }

  Future<void> _onSongComplete() async {
    // Add duration to totalSeconds if duration known
    final dur = _currentDuration.inSeconds;
    if (dur > 0) {
      totalSeconds += dur;
    } else {
      // fallback: add 180 seconds
      totalSeconds += 180;
    }
    await _savePersistentState();
    setState(() {});
    // reset player so repeated plays record again
    await _player.stop();
  }

  String _formatTotalTime(int seconds) {
    final hours = seconds ~/ 3600;
    final minutes = (seconds % 3600) ~/ 60;
    final secs = seconds % 60;
    if (hours > 0) return '${hours}h ${minutes}m ${secs}s';
    if (minutes > 0) return '${minutes}m ${secs}s';
    return '${secs}s';
  }

  String _getTitleById(String id) {
    final found = songs.firstWhere((s) => s.id == id, orElse: () => SongItem(id: id, title: id, assetPath: ''));
    return found.title;
  }

  Future<void> _removeFavorite(String id) async {
    favorites.remove(id);
    await _savePersistentState();
    setState(() {});
  }

  Future<void> _resetAllData() async {
    playLog.clear();
    favorites.clear();
    totalSeconds = 0;
    await _savePersistentState();
    setState(() {});
  }

  // UI helpers
  Widget _buildSongTile(int index) {
    final song = songs[index];
    final isCurrent = _currentIndex == index;
    final isFav = favorites.contains(song.id);
    final recentPlays = playLog[song.id]?.length ?? 0;

    return Card(
      elevation: 2,
      margin: EdgeInsets.symmetric(vertical: 6, horizontal: 12),
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: isFav ? Colors.amber : Colors.indigoAccent,
          child: isFav ? Icon(Icons.star, color: Colors.white) : Icon(Icons.music_note, color: Colors.white),
        ),
        title: Text(song.title),
        subtitle: Text('Plays (last 24h): $recentPlays'),
        trailing: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (isCurrent) Text(_formatPosition()),
            IconButton(
              icon: Icon(isCurrent && _isPlaying ? Icons.pause_circle_filled : Icons.play_circle_fill, size: 32, color: Colors.indigo),
              onPressed: () async {
                if (isCurrent) {
                  if (_isPlaying) {
                    await _pauseSong();
                  } else {
                    await _player.play();
                  }
                } else {
                  await _playSong(index);
                }
              },
            ),
            PopupMenuButton<String>(
              onSelected: (val) async {
                if (val == 'fav') {
                  if (isFav) {
                    await _removeFavorite(song.id);
                  } else {
                    favorites.add(song.id);
                    await _savePersistentState();
                    setState(() {});
                  }
                } else if (val == 'info') {
                  _showSongInfo(song);
                }
              },
              itemBuilder: (context) => <PopupMenuEntry<String>>[
                PopupMenuItem(value: 'fav', child: Text(isFav ? 'Remove Favorite' : 'Add Favorite')),
                PopupMenuItem(value: 'info', child: Text('Song Info')),
              ],
            ),
          ],
        ),
      ),
    );
  }

  String _formatPosition() {
    final pos = _currentPosition;
    final dur = _currentDuration;
    String p = _twoDigits(pos.inMinutes.remainder(60)) + ':' + _twoDigits(pos.inSeconds.remainder(60));
    String d = dur.inMinutes.remainder(60).toString().padLeft(2, '0') + ':' + dur.inSeconds.remainder(60).toString().padLeft(2, '0');
    return '$p / $d';
  }

  String _twoDigits(int n) => n.toString().padLeft(2, '0');

  void _showSongInfo(SongItem song) {
    final plays = playLog[song.id] ?? [];
    final times = plays.map((t) => DateFormat('yyyy-MM-dd HH:mm').format(t)).join('\n');
    showDialog(context: context, builder: (_) {
      return AlertDialog(
        title: Text(song.title),
        content: SizedBox(
          width: double.maxFinite,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text('Asset: ${song.assetPath}'),
              SizedBox(height: 8),
              Text('Recent Plays (last 24h):'),
              SizedBox(height: 6),
              if (times.isNotEmpty) Text(times) else Text('No plays recorded'),
            ],
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: Text('Close'))
        ],
      );
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Advanced Music App'),
        actions: [
          IconButton(
            icon: Icon(Icons.refresh),
            onPressed: () => setState(() {}),
            tooltip: 'Refresh UI',
          ),
          PopupMenuButton<String>(
            onSelected: (v) {
              if (v == 'reset') _resetAllData();
            },
            itemBuilder: (_) => [
              PopupMenuItem(value: 'reset', child: Text('Reset Data')),
            ],
          ),
        ],
      ),
      body: SafeArea(
        child: Column(
          children: [
            // Top metrics
            Container(
              padding: EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              color: Colors.indigo.shade50,
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text('Total Listening Time', style: TextStyle(fontSize: 12, color: Colors.grey[700])),
                    SizedBox(height: 6),
                    Text(_formatTotalTime(totalSeconds), style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                  ]),
                  Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
                    Text('Favorites', style: TextStyle(fontSize: 12, color: Colors.grey[700])),
                    SizedBox(height: 6),
                    Text('${favorites.length}', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                  ]),
                ],
              ),
            ),

            // Song list
            Expanded(
              child: ListView.builder(
                itemCount: songs.length,
                itemBuilder: (context, i) => _buildSongTile(i),
              ),
            ),

            // Favorite list & controls
            Container(
              padding: EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.grey.shade100,
                border: Border(top: BorderSide(color: Colors.grey.shade300)),
              ),
              child: Row(
                children: [
                  Expanded(
                    child: favorites.isEmpty
                        ? Text('No favorites yet. Play a song 4+ times within 24 hours to auto-favorite it.')
                        : SingleChildScrollView(
                            scrollDirection: Axis.horizontal,
                            child: Row(
                              children: favorites.map((id) {
                                final title = _getTitleById(id);
                                return Padding(
                                  padding: EdgeInsets.only(right: 8.0),
                                  child: InputChip(
                                    label: Text(title),
                                    avatar: Icon(Icons.star, color: Colors.amber),
                                    onDeleted: () => _removeFavorite(id),
                                  ),
                                );
                              }).toList(),
                            ),
                          ),
                  ),
                  SizedBox(width: 8),
                  ElevatedButton.icon(
                    icon: Icon(Icons.stop_circle_outlined),
                    label: Text('Stop'),
                    style: ElevatedButton.styleFrom(primary: Colors.redAccent),
                    onPressed: _stopSong,
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
