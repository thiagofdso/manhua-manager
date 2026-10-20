import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'controllers/manhua_controller.dart';
import 'screens/home_screen.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(
    MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => ManhuaController()),
      ],
      child: const ManhuaApp(),
    ),
  );
}

class ManhuaApp extends StatelessWidget {
  const ManhuaApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Manhua Manager',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        brightness: Brightness.dark,
        scaffoldBackgroundColor: const Color(0xFF121214),
        cardColor: const Color(0xFF202024),
        colorScheme: const ColorScheme.dark(
          primary: Color(0xFF8257E6),
          secondary: Color(0xFF9466FF),
          surface: Color(0xFF202024),
        ),
        appBarTheme: const AppBarTheme(
          backgroundColor: Color(0xFF18181B),
          elevation: 0,
          centerTitle: false,
        ),
        useMaterial3: true,
      ),
      home: const HomeScreen(),
    );
  }
}
