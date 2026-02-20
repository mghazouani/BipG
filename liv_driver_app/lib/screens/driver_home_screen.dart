import 'package:flutter/material.dart';
import '../config.dart';
import '../services/api_service.dart';
import '../services/health_service.dart';
import 'mission_screen.dart';

class DriverHomeScreen extends StatefulWidget {
  const DriverHomeScreen({super.key});

  @override
  State<DriverHomeScreen> createState() => _DriverHomeScreenState();
}

class _DriverHomeScreenState extends State<DriverHomeScreen> {
  bool _loading = false;
  bool _hasLoaded = false;
  String? _error;
  Map<String, dynamic>? _mission;

  HealthResult? _health;
  bool _healthChecking = false;

  @override
  void initState() {
    super.initState();
    _checkHealth();
  }

  Future<void> _checkHealth() async {
    setState(() => _healthChecking = true);
    final result = await HealthService().check();
    if (mounted) setState(() { _health = result; _healthChecking = false; });
  }

  Future<void> _loadMission() async {
    setState(() {
      _loading = true;
      _error = null;
      _mission = null;
    });
    try {
      final mission = await ApiService().getActiveMission();
      if (!mounted) return;
      setState(() {
        _loading = false;
        _hasLoaded = true;
        _mission = mission;
      });
      if (mission != null) {
        Navigator.of(context).push(
          MaterialPageRoute(
            builder: (_) => MissionScreen(mission: mission),
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _loading = false;
          _hasLoaded = true;
          _error = e.toString().replaceFirst('Exception: ', '');
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('LIV Driver'),
        centerTitle: true,
      ),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: [
                    Text(
                      'Driver ID: $driverId',
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'API: $apiBaseUrl',
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                    const SizedBox(height: 12),
                    _HealthBadge(
                      result: _health,
                      checking: _healthChecking,
                      onRefresh: _checkHealth,
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 24),
            FilledButton.icon(
              onPressed: _loading ? null : _loadMission,
              icon: _loading
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.directions_car),
              label: Text(_loading ? 'Loading...' : 'Load Active Mission'),
            ),
            if (_error != null) ...[
              const SizedBox(height: 16),
              Card(
                color: Theme.of(context).colorScheme.errorContainer,
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Text(
                    _error!,
                    style: TextStyle(
                      color: Theme.of(context).colorScheme.onErrorContainer,
                    ),
                  ),
                ),
              ),
            ],
            if (_hasLoaded && !_loading && _mission == null && _error == null) ...[
              const SizedBox(height: 24),
              const Center(child: Text('No active mission')),
            ],
          ],
        ),
      ),
    );
  }
}

class _HealthBadge extends StatelessWidget {
  final HealthResult? result;
  final bool checking;
  final VoidCallback onRefresh;

  const _HealthBadge({
    required this.result,
    required this.checking,
    required this.onRefresh,
  });

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    if (checking) {
      return Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const SizedBox(width: 12, height: 12, child: CircularProgressIndicator(strokeWidth: 2)),
          const SizedBox(width: 8),
          Text('Backend…', style: Theme.of(context).textTheme.bodySmall),
        ],
      );
    }
    final ok = result?.reachable ?? false;
    final label = ok
        ? 'Backend: OK${result!.latencyMs != null ? ' (${result!.latencyMs}ms)' : ''}'
        : 'Backend: Down${result?.error != null ? ' — ${result!.error}' : ''}';
    return GestureDetector(
      onTap: onRefresh,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
        decoration: BoxDecoration(
          color: ok ? cs.primaryContainer : cs.errorContainer,
          borderRadius: BorderRadius.circular(12),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              ok ? Icons.check_circle_outline : Icons.error_outline,
              size: 14,
              color: ok ? cs.onPrimaryContainer : cs.onErrorContainer,
            ),
            const SizedBox(width: 6),
            Text(
              label,
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                    color: ok ? cs.onPrimaryContainer : cs.onErrorContainer,
                  ),
            ),
          ],
        ),
      ),
    );
  }
}
