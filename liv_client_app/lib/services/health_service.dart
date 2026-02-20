import 'package:http/http.dart' as http;
import '../config.dart';

class HealthResult {
  final bool reachable;
  final int? latencyMs;
  final String? error;

  const HealthResult({required this.reachable, this.latencyMs, this.error});
}

class HealthService {
  static final HealthService _instance = HealthService._();
  factory HealthService() => _instance;
  HealthService._();

  Future<HealthResult> check() async {
    final sw = Stopwatch()..start();
    try {
      final r = await http
          .get(Uri.parse('$apiBaseUrl/health'))
          .timeout(const Duration(seconds: 5));
      sw.stop();
      if (r.statusCode == 200) {
        return HealthResult(reachable: true, latencyMs: sw.elapsedMilliseconds);
      }
      return HealthResult(
        reachable: false,
        latencyMs: sw.elapsedMilliseconds,
        error: 'HTTP ${r.statusCode}',
      );
    } catch (e) {
      sw.stop();
      return HealthResult(reachable: false, error: e.runtimeType.toString());
    }
  }
}
