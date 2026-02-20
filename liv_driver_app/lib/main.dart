import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'screens/driver_home_screen.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  SystemChrome.setPreferredOrientations([
    DeviceOrientation.portraitUp,
    DeviceOrientation.landscapeLeft,
  ]);
  runApp(const LivDriverApp());
}

class LivDriverApp extends StatelessWidget {
  const LivDriverApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'LIV Driver',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.orange, brightness: Brightness.light),
        useMaterial3: true,
      ),
      home: const DriverHomeScreen(),
    );
  }
}
