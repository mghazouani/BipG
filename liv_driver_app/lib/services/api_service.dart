import 'dart:convert';
import 'package:http/http.dart' as http;
import '../config.dart';

class ApiService {
  static final ApiService _instance = ApiService._();
  factory ApiService() => _instance;
  ApiService._();

  String get _base => apiBaseUrl;

  Future<Map<String, dynamic>?> getActiveMission() async {
    final r = await http.get(Uri.parse('$_base/drivers/$driverId/active-mission'));
    if (r.statusCode != 200) throw Exception(r.body.isNotEmpty ? r.body : 'Failed');
    final data = jsonDecode(r.body) as Map<String, dynamic>;
    final mission = data['active_mission'];
    return mission as Map<String, dynamic>?;
  }

  Future<void> setDeliveryState(int deliveryId, String state) async {
    final r = await http.post(
      Uri.parse('$_base/deliveries/$deliveryId/state'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'state': state}),
    );
    if (r.statusCode != 200 && r.statusCode != 201) {
      throw Exception(r.body.isNotEmpty ? r.body : 'Set state failed');
    }
  }

  Future<void> collectPayment(int deliveryId, {String method = 'cash', double? amount, String? ref}) async {
    final body = <String, dynamic>{'method': method};
    if (amount != null) body['amount'] = amount;
    if (ref != null) body['ref'] = ref;
    final r = await http.post(
      Uri.parse('$_base/deliveries/$deliveryId/collect-payment'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(body),
    );
    if (r.statusCode != 200 && r.statusCode != 201) {
      throw Exception(r.body.isNotEmpty ? r.body : 'Collect payment failed');
    }
  }
}
