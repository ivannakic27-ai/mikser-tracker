import 'package:flutter/material.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import 'config.dart';
import 'data.dart';
import 'screens/alerts.dart';
import 'screens/all_models.dart';
import 'screens/compare.dart';
import 'screens/home.dart';
import 'screens/thresholds.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Supabase.initialize(url: supabaseUrl, publishableKey: supabaseAnonKey);
  runApp(const MikserApp());
}

class MikserApp extends StatelessWidget {
  const MikserApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Mikser tracker',
      debugShowCheckedModeBanner: false,
      themeMode: ThemeMode.dark,
      darkTheme: ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.deepOrange, brightness: Brightness.dark),
      ),
      theme: ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.deepOrange, brightness: Brightness.dark),
      ),
      home: const AuthGate(),
    );
  }
}

class AuthGate extends StatelessWidget {
  const AuthGate({super.key});

  @override
  Widget build(BuildContext context) {
    return StreamBuilder<AuthState>(
      stream: Supabase.instance.client.auth.onAuthStateChange,
      builder: (context, snapshot) {
        final session = Supabase.instance.client.auth.currentSession;
        return session == null ? const LoginScreen() : const Shell();
      },
    );
  }
}

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _email = TextEditingController();
  final _pass = TextEditingController();
  String? _error;
  bool _busy = false;

  Future<void> _login() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await Supabase.instance.client.auth
          .signInWithPassword(email: _email.text.trim(), password: _pass.text);
    } on AuthException catch (e) {
      setState(() => _error = e.message);
    } catch (e) {
      setState(() => _error = 'Greška: $e');
    }
    if (mounted) setState(() => _busy = false);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 380),
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Text('🥖 Mikser tracker', style: TextStyle(fontSize: 26, fontWeight: FontWeight.bold)),
                const SizedBox(height: 8),
                const Text('Prijava (samo vlasnik)'),
                const SizedBox(height: 24),
                TextField(
                  controller: _email,
                  keyboardType: TextInputType.emailAddress,
                  decoration: const InputDecoration(labelText: 'E-mail', border: OutlineInputBorder()),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: _pass,
                  obscureText: true,
                  decoration: const InputDecoration(labelText: 'Lozinka', border: OutlineInputBorder()),
                  onSubmitted: (_) => _login(),
                ),
                if (_error != null)
                  Padding(
                    padding: const EdgeInsets.only(top: 12),
                    child: Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
                  ),
                const SizedBox(height: 16),
                FilledButton(
                  onPressed: _busy ? null : _login,
                  child: Text(_busy ? 'Prijava...' : 'Prijavi se'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class Shell extends StatefulWidget {
  const Shell({super.key});

  @override
  State<Shell> createState() => _ShellState();
}

class _ShellState extends State<Shell> {
  int _tab = 0;

  @override
  void initState() {
    super.initState();
    AppState.i.load();
  }

  @override
  Widget build(BuildContext context) {
    const pages = <Widget>[HomeScreen(), AllModelsScreen(), CompareScreen(), ThresholdsScreen(), AlertsScreen()];
    return Scaffold(
      body: SafeArea(
        child: Column(
          children: [
            ListenableBuilder(
              listenable: AppState.i,
              builder: (context, _) {
                if (AppState.i.offline) {
                  return Container(
                    width: double.infinity,
                    color: Colors.amber.shade900,
                    padding: const EdgeInsets.all(6),
                    child: const Text('Offline: prikazani su zadnji spremljeni podaci',
                        textAlign: TextAlign.center, style: TextStyle(color: Colors.white)),
                  );
                }
                return const SizedBox.shrink();
              },
            ),
            Expanded(child: IndexedStack(index: _tab, children: pages)),
          ],
        ),
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _tab,
        onDestinationSelected: (i) => setState(() => _tab = i),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.dashboard_outlined), label: 'Pregled'),
          NavigationDestination(icon: Icon(Icons.list_alt), label: 'Svi'),
          NavigationDestination(icon: Icon(Icons.compare_arrows), label: 'Usporedba'),
          NavigationDestination(icon: Icon(Icons.tune), label: 'Pragovi'),
          NavigationDestination(icon: Icon(Icons.notifications_outlined), label: 'Alarmi'),
        ],
      ),
    );
  }
}
