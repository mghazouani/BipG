/// API base URL config for LIV client app.
///
/// Single source of truth: [getApiBaseUrl] / [apiBaseUrl] and [wsBaseUrl].
///
/// Modes (default: USB via ADB reverse):
/// - **ADB reverse** (real Android device, USB, default): 127.0.0.1. Run
///   `adb reverse tcp:8000 tcp:8000` then `flutter run -d <device>`.
/// - **Android emulator**: set [useAndroidEmulator] = true. Host: 10.0.2.2.
/// - **Real device on LAN**: run with `--dart-define=USE_ADB_REVERSE=false` and
///   `--dart-define=DEVICE_HOST=192.168.1.42` (phone and PC on same Wi‑Fi).
///
/// Ports: override with `--dart-define=API_PORT=8000` and `--dart-define=WS_PORT=8000`.

const bool useAndroidEmulator = false;

/// When true (default), use 127.0.0.1 so the app on a real device reaches the host via ADB reverse (USB).
/// Set to false for LAN: --dart-define=USE_ADB_REVERSE=false
const bool useAdbReverse = bool.fromEnvironment(
  'USE_ADB_REVERSE',
  defaultValue: true,
);

/// Host for real device on LAN when not using ADB reverse. Set via dart-define:
/// --dart-define=DEVICE_HOST=192.168.1.42
const String deviceHost = String.fromEnvironment(
  'DEVICE_HOST',
  defaultValue: '192.168.1.126',
);

const int apiPort = int.fromEnvironment('API_PORT', defaultValue: 8000);
const int wsPort = int.fromEnvironment('WS_PORT', defaultValue: 8000);

const String _emulatorHost = '10.0.2.2';

String get _apiHost {
  if (useAdbReverse) return '127.0.0.1';
  return useAndroidEmulator ? _emulatorHost : deviceHost;
}

/// Single source of truth for the API base URL. All HTTP calls should use this.
String getApiBaseUrl() => 'http://$_apiHost:$apiPort';

String get apiBaseUrl => getApiBaseUrl();

String get wsBaseUrl => 'ws://$_apiHost:$wsPort';
