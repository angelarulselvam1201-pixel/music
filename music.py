import 'package:flutter/material.dart';
import 'package:audioplayers/audioplayers.dart';
import 'dart:async';
import 'dart:math';

void main() {
  runApp(MusicToooApp());
}

class MusicToooApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: "Musictooo",
      debugShowCheckedModeBanner: false,
      theme: ThemeData.dark().copyWith(
        scaffoldBackgroundColor: Color(0xFF0B031A),
        primaryColor: Color(0xFF6A0DAD),
        colorScheme: ColorScheme.dark(
          primary: Color(0xFF6A0DAD),
          secondary: Color(0xFF9B4BFF),
        ),
      ),
      home: MusicHome(),
    );
  }
}

class SongData {
  final String title;
  final String assetPath;
  final String albumArt;

  int playCount = 0;
  DateTime lastPlayed = DateTime.now();

  SongData(this.title, this.assetPath, this.albumArt);
}

class MusicHome extends StatefulWidget {
  @override
  State<MusicHome> createState() => _MusicHomeState();
}

class _MusicHomeState extends State<MusicHome>
    with SingleTickerProviderStateMixin {
  final AudioPlayer player = AudioPlayer();
  SongData currentSong;
  Timer equalizerTimer;

  List<int> equalizerLevels = [5, 10, 6, 12, 8];
  bool isPlaying = false;
  Duration totalPlayTime = Duration.zero;

  AnimationController rotationController;

  List<SongData> songs = [
    SongData("Dream Wave", "assets/song1.mp3", "assets/album1.jpg"),
    SongData("Purple Skies", "assets/song2.mp3", "assets/album2.jpg"),
    SongData("Midnight Echo", "assets/song3.mp3", "assets/album3.jpg"),
  ];

  List<SongData> get favorites {
    return songs.where((s) => s.playCount >= 4).toList();
  }

  @override
  void initState() {
    super.initState();

    currentSong = songs[0];

    rotationController = AnimationController(
      vsync: this,
      duration: Duration(seconds: 12),
    );

    equalizerTimer =
        Timer.periodic(Duration(milliseconds: 160), (timer) {
      setState(() {
        equalizerLevels = List.generate(
          5,
          (index) => Random().nextInt(20) + 5,
        );
      });
    });

    player.onPlayerComplete.listen((event) {
      setState(() {
        isPlaying = false;
        rotationController.stop();

        currentSong.playCount += 1;
        currentSong.lastPlayed = DateTime.now();
      });
    });

    player.onPositionChanged.listen((position) {
      setState(() {
        totalPlayTime += Duration(seconds: 1);
      });
    });
  }

  @override
  void dispose() {
    player.dispose();
    equalizerTimer.cancel();
    rotationController.dispose();
    super.dispose();
  }

  Future<void> playSong(SongData song) async {
    await player.stop();
    await player.play(AssetSource(song.assetPath.split("/").last));

    setState(() {
      currentSong = song;
      isPlaying = true;
      rotationController.repeat();
      song.playCount += 1;
      song.lastPlayed = DateTime.now();
    });
  }

  void togglePlayPause() async {
    if (isPlaying) {
      await player.pause();
      rotationController.stop();
    } else {
      await player.resume();
      rotationController.repeat();
    }

    setState(() {
      isPlaying = !isPlaying;
    });
  }

  Widget buildEqualizer() {
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: equalizerLevels.map((level) {
        return Padding(
          padding: EdgeInsets.symmetric(horizontal: 3),
          child: AnimatedContainer(
            duration: Duration(milliseconds: 150),
            width: 10,
            height: level.toDouble(),
            decoration: BoxDecoration(
              color: Color(0xFF9B4BFF),
              borderRadius: BorderRadius.circular(5),
            ),
          ),
        );
      }).toList(),
    );
  }

  Widget buildSongTile(SongData song) {
    return ListTile(
      leading: CircleAvatar(
        backgroundImage: AssetImage(song.albumArt),
      ),
      title: Text(song.title),
      subtitle: Text("Plays: ${song.playCount}"),
      trailing: Icon(Icons.play_arrow, color: Colors.white),
      onTap: () => playSong(song),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text("M U S I C T O O O"),
        backgroundColor: Colors.black,
      ),

      body: SingleChildScrollView(
        child: Column(
          children: [
            SizedBox(height: 20),

            RotationTransition(
              turns: rotationController,
              child: Container(
                width: 240,
                height: 240,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  border: Border.all(
                    color: Color(0xFF6A0DAD),
                    width: 6,
                  ),
                  image: DecorationImage(
                    image: AssetImage(currentSong.albumArt),
                    fit: BoxFit.cover,
                  ),
                ),
              ),
            ),
            SizedBox(height: 20),

            Text(
              currentSong.title,
              style: TextStyle(fontSize: 24, color: Colors.white),
            ),

            SizedBox(height: 16),
            buildEqualizer(),
            SizedBox(height: 20),

            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                IconButton(
                  icon: Icon(
                    isPlaying ? Icons.pause_circle : Icons.play_circle,
                    size: 60,
                    color: Color(0xFF9B4BFF),
                  ),
                  onPressed: togglePlayPause,
                ),
              ],
            ),

            SizedBox(height: 20),
            Text(
              "Total Listening Time: ${totalPlayTime.inMinutes} min",
              style: TextStyle(color: Colors.grey),
            ),

            SizedBox(height: 30),
            Divider(color: Colors.purple),

            Text(
              "All Songs",
              style: TextStyle(fontSize: 22),
            ),
            Column(children: songs.map(buildSongTile).toList()),

            SizedBox(height: 30),
            Divider(color: Colors.purple),
            Text(
              "Favorites",
              style: TextStyle(fontSize: 22),
            ),

            Column(
              children: favorites.isEmpty
                  ? [Text("No favorites yet")]
                  : favorites.map(buildSongTile).toList(),
            ),

            SizedBox(height: 40),
          ],
        ),
      ),
    );
  }
}
