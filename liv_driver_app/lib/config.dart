/// API base URL config for LIV driver app.
///
/// Modes (default: USB via ADB reverse):
/// - **ADB reverse** (real Android device, USB, default): 127.0.0.1. Run
///   `adb reverse tcp:8000 tcp:8000` then `flutter run -d <device>`.
/// - **Android emulator**: set --dart-define=USE_ADB_REVERSE=false, host: 10.0.2.2.
/// - **Real device on LAN**: --dart-define=USE_ADB_REVERSE=false
///   and --dart-define=DEVICE_HOST=192.168.1.42.
///
/// Ports: override with --dart-define=API_PORT=8000 and --dart-define=WS_PORT=8000.

/// When true (default), use 127.0.0.1 so the app on a real device reaches the host via ADB reverse (USB).
const bool useAdbReverse = bool.fromEnvironment(
  'USE_ADB_REVERSE',
  defaultValue: true,
);

/// Host for real device on LAN when not using ADB reverse.
const String deviceHost = String.fromEnvironment(
  'DEVICE_HOST',
  defaultValue: '192.168.1.10',
);

const int apiPort = int.fromEnvironment('API_PORT', defaultValue: 8000);
const int wsPort = int.fromEnvironment('WS_PORT', defaultValue: 8000);

const String _emulatorHost = '10.0.2.2';

String get _apiHost => useAdbReverse ? '127.0.0.1' : _emulatorHost;

/// Single source of truth for the API base URL.
String get apiBaseUrl => 'http://$_apiHost:$apiPort';

String get wsBaseUrl => 'ws://$_apiHost:$wsPort';

/// Driver ID for this app (demo: match Odoo user ID).
const int driverId = 2;

/// WS token secret (demo only; must match backend WS_SECRET).
const String wsSecret = 'supersecretlivkey';
