import 'dart:convert';
import 'package:http/http.dart' as http;
import '../config.dart';

class ApiService {
  static final ApiService _instance = ApiService._();
  factory ApiService() => _instance;

  ApiService._();

  String get _base => apiBaseUrl;

  Future<Map<String, dynamic>> placeOrder({
    required String customerName,
    required String phone,
    required String address,
    int qty = 1,
  }) async {
    final r = await http.post(
      Uri.parse('$_base/client/orders'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'customer_name': customerName,
        'phone': phone,
        'address': address,
        'qty': qty,
      }),
    );
    if (r.statusCode != 200 && r.statusCode != 201) {
      throw Exception(r.body.isNotEmpty ? r.body : 'Failed to place order');
    }
    return jsonDecode(r.body) as Map<String, dynamic>;
  }

  Future<void> confirmOrder(int saleOrderId) async {
    final r = await http.post(
      Uri.parse('$_base/backoffice/orders/$saleOrderId/confirm'),
      headers: {'Content-Type': 'application/json'},
    );
    if (r.statusCode != 200 && r.statusCode != 201) {
      throw Exception(r.body.isNotEmpty ? r.body : 'Confirm failed');
    }
  }

  Future<Map<String, dynamic>> createMission(int saleOrderId) async {
    final r = await http.post(
      Uri.parse('$_base/backoffice/orders/$saleOrderId/create-mission'),
      headers: {'Content-Type': 'application/json'},
    );
    if (r.statusCode != 200 && r.statusCode != 201) {
      throw Exception(r.body.isNotEmpty ? r.body : 'Create mission failed');
    }
    return jsonDecode(r.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> getDelivery(int deliveryId) async {
    final r = await http.get(Uri.parse('$_base/deliveries/$deliveryId'));
    if (r.statusCode != 200) {
      throw Exception(r.body.isNotEmpty ? r.body : 'Failed to get delivery');
    }
    return jsonDecode(r.body) as Map<String, dynamic>;
  }
}
