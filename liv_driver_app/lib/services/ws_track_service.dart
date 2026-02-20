import 'dart:async';
import 'dart:convert';
import 'package:crypto/crypto.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import '../config.dart';

/// Generates WS token: base64(driver_id:delivery_id:timestamp:signature).
String buildWsToken(int deliveryId) {
  final ts = (DateTime.now().millisecondsSinceEpoch / 1000).floor();
  final payload = '$driverId:$deliveryId:$ts';
  final key = utf8.encode(wsSecret);
  final bytes = utf8.encode(payload);
  final hmac = Hmac(sha256, key);
  final sig = hmac.convert(bytes).toString();
  final raw = '$payload:$sig';
  return base64Encode(utf8.encode(raw));
}

/// Sends tracking position every [intervalSeconds]. Call [close] to stop.
class WsTrackService {
  WebSocketChannel? _channel;
  Timer? _timer;
  final int deliveryId;
  final int intervalSeconds;
  final void Function(String)? onError;
  final void Function(Map<String, dynamic>)? onAck;

  WsTrackService({
    required this.deliveryId,
    this.intervalSeconds = 10,
    this.onError,
    this.onAck,
  });

  bool get isActive => _channel != null;

  void start(Future<Map<String, dynamic>> Function() getPosition) async {
    if (_channel != null) return;
    final token = buildWsToken(deliveryId);
    final uri = Uri.parse('$wsBaseUrl/ws/track?token=$token');
    try {
      _channel = WebSocketChannel.connect(uri);
      _channel!.stream.listen(
        (data) {
          try {
            final map = jsonDecode(data as String) as Map<String, dynamic>;
            if (map['error'] != null) {
              onError?.call(map['error'] as String? ?? 'unknown');
              return;
            }
            if (map['ack'] == true) onAck?.call(map);
          } catch (_) {}
        },
        onError: (e) => onError?.call(e.toString()),
        onDone: () => _channel = null,
        cancelOnError: false,
      );
      _timer = Timer.periodic(Duration(seconds: intervalSeconds), (_) async {
        if (_channel == null) return;
        try {
          final pos = await getPosition();
          final msg = {
            'delivery_id': deliveryId,
            'driver_id': driverId,
            'lat': pos['lat'],
            'lon': pos['lon'],
            'ts': DateTime.now().toUtc().toIso8601String(),
            if (pos['speed'] != null) 'speed': pos['speed'],
            if (pos['heading'] != null) 'heading': pos['heading'],
          };
          _channel!.sink.add(jsonEncode(msg));
        } catch (e) {
          onError?.call(e.toString());
        }
      });
    } catch (e) {
      onError?.call(e.toString());
    }
  }

  void close() {
    _timer?.cancel();
    _timer = null;
    _channel?.sink.close();
    _channel = null;
  }
}
