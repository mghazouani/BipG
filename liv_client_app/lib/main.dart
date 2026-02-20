import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'screens/order_screen.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  SystemChrome.setPreferredOrientations([
    DeviceOrientation.portraitUp,
    DeviceOrientation.landscapeLeft,
  ]);
  runApp(const LivClientApp());
}

class LivClientApp extends StatelessWidget {
  const LivClientApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'LIV Client',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.teal, brightness: Brightness.light),
        useMaterial3: true,
      ),
      home: const OrderScreen(),
    );
  }
}
