import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import '../services/api_service.dart';

class TrackingScreen extends StatefulWidget {
  final int saleOrderId;
  final int? deliveryId;

  const TrackingScreen({
    super.key,
    required this.saleOrderId,
    this.deliveryId,
  });

  @override
  State<TrackingScreen> createState() => _TrackingScreenState();
}

class _TrackingScreenState extends State<TrackingScreen> {
  int? _deliveryId;
  Map<String, dynamic>? _delivery;
  String? _error;
  Timer? _pollTimer;
  final MapController _mapController = MapController();
  final ApiService _api = ApiService();

  @override
  void initState() {
    super.initState();
    _deliveryId = widget.deliveryId;
    _fetch();
    _pollTimer = Timer.periodic(const Duration(seconds: 2), (_) => _fetch());
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    super.dispose();
  }

  Future<void> _fetch() async {
    if (_deliveryId == null) {
      try {
        await _api.confirmOrder(widget.saleOrderId);
        final mission = await _api.createMission(widget.saleOrderId);
        final id = mission['delivery_id'] ?? mission['id'];
        if (id != null && mounted) setState(() => _deliveryId = id as int);
      } catch (_) {
        if (mounted) setState(() => _error = 'Waiting for mission...');
        return;
      }
    }
    if (_deliveryId == null) return;
    try {
      final data = await _api.getDelivery(_deliveryId!);
      if (mounted) setState(() {
        _delivery = data;
        _error = null;
      });
    } catch (e) {
      if (mounted) setState(() => _error = e.toString().replaceFirst('Exception: ', ''));
    }
  }

  LatLng? get _driverPosition {
    if (_delivery == null) return null;
    final redis = _delivery!['redis_last'] ?? _delivery!['last_location'];
    if (redis != null) {
      final lat = redis['lat'] as num?;
      final lon = redis['lon'] as num?;
      if (lat != null && lon != null) return LatLng(lat.toDouble(), lon.toDouble());
    }
    final d = _delivery!['delivery'] as Map<String, dynamic>?;
    if (d != null) {
      final lat = d['last_lat'] as num?;
      final lon = d['last_lon'] as num?;
      if (lat != null && lon != null) return LatLng(lat.toDouble(), lon.toDouble());
    }
    return null;
  }

  String get _stateText {
    final d = _delivery?['delivery'] as Map<String, dynamic>?;
    final s = d?['state'] as String? ?? '—';
    return s;
  }

  String? get _lastTs {
    final redis = _delivery?['redis_last'] ?? _delivery?['last_location'];
    if (redis != null && redis['ts'] != null) return redis['ts'] as String?;
    final d = _delivery?['delivery'] as Map<String, dynamic>?;
    return d?['last_ts'] as String?;
  }

  @override
  Widget build(BuildContext context) {
    final driverPos = _driverPosition;
    return Scaffold(
      appBar: AppBar(
        title: const Text('Tracking'),
        centerTitle: true,
      ),
      body: Column(
        children: [
          Card(
            margin: const EdgeInsets.all(12),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Order #${widget.saleOrderId}',
                      style: Theme.of(context).textTheme.titleMedium),
                  if (_deliveryId != null)
                    Text('Delivery #$_deliveryId',
                        style: Theme.of(context).textTheme.bodyMedium),
                  const SizedBox(height: 4),
                  Text('State: $_stateText',
                      style: Theme.of(context).textTheme.bodyMedium),
                  if (_error != null)
                    Text(_error!,
                        style: TextStyle(
                          color: Theme.of(context).colorScheme.error,
                          fontSize: 12,
                        )),
                  if (_lastTs != null)
                    Text('Last update: $_lastTs',
                        style: Theme.of(context).textTheme.bodySmall),
                ],
              ),
            ),
          ),
          Expanded(
            child: driverPos != null
                ? LayoutBuilder(
                    builder: (_, __) {
                      WidgetsBinding.instance.addPostFrameCallback((_) {
                        _mapController.move(driverPos, 14);
                      });
                      return FlutterMap(
                        mapController: _mapController,
                        options: MapOptions(
                          initialCenter: driverPos,
                          initialZoom: 14,
                          onMapReady: () => _mapController.move(driverPos, 14),
                        ),
                    children: [
                      TileLayer(
                        urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                        userAgentPackageName: 'com.example.liv_client_app',
                      ),
                      MarkerLayer(
                        markers: [
                          Marker(
                            point: driverPos,
                            width: 40,
                            height: 40,
                            child: const Icon(
                              Icons.delivery_dining,
                              color: Colors.blue,
                              size: 40,
                            ),
                          ),
                        ],
                      ),
                    ],
                  );
                    },
                  )
                : Center(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const CircularProgressIndicator(),
                        const SizedBox(height: 16),
                        Text(
                          'Driver is on the way',
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        if (_error != null)
                          Padding(
                            padding: const EdgeInsets.only(top: 8),
                            child: Text(
                              _error!,
                              style: Theme.of(context).textTheme.bodySmall,
                              textAlign: TextAlign.center,
                            ),
                          ),
                      ],
                    ),
                  ),
          ),
        ],
      ),
    );
  }
}
