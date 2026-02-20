import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:geolocator/geolocator.dart';
import 'package:latlong2/latlong.dart';
import '../services/api_service.dart';
import '../services/ws_track_service.dart';

class MissionScreen extends StatefulWidget {
  final Map<String, dynamic> mission;

  const MissionScreen({super.key, required this.mission});

  @override
  State<MissionScreen> createState() => _MissionScreenState();
}

class _MissionScreenState extends State<MissionScreen> {
  int get _deliveryId => widget.mission['id'] as int? ?? widget.mission['delivery_id'] as int? ?? 0;
  String get _customerName => widget.mission['customer_name'] as String? ?? '—';
  String get _address => widget.mission['address'] as String? ?? '—';
  String get _state => widget.mission['state'] as String? ?? '—';

  final ApiService _api = ApiService();
  WsTrackService? _wsTrack;
  Position? _currentPosition;
  String? _error;
  bool _loading = false;
  final MapController _mapController = MapController();

  @override
  void initState() {
    super.initState();
    _getLocation();
  }

  @override
  void dispose() {
    _wsTrack?.close();
    super.dispose();
  }

  Future<void> _getLocation() async {
    final ok = await Geolocator.isLocationServiceEnabled();
    if (!ok) {
      setState(() => _error = 'Location disabled');
      return;
    }
    var permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
    }
    if (permission == LocationPermission.denied || permission == LocationPermission.deniedForever) {
      setState(() => _error = 'Location permission denied');
      return;
    }
    try {
      final pos = await Geolocator.getCurrentPosition(desiredAccuracy: LocationAccuracy.medium);
      if (mounted) setState(() => _currentPosition = pos);
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    }
  }

  Future<Map<String, dynamic>> _getPositionForWs() async {
    await _getLocation();
    final p = _currentPosition;
    if (p == null) throw Exception('No position');
    return {'lat': p.latitude, 'lon': p.longitude};
  }

  void _startTracking() {
    if (_wsTrack != null) return;
    _wsTrack = WsTrackService(
      deliveryId: _deliveryId,
      intervalSeconds: 10,
      onError: (e) => mounted ? setState(() => _error = e) : null,
      onAck: (_) => mounted ? setState(() => _error = null) : null,
    );
    _wsTrack!.start(_getPositionForWs);
    setState(() {});
  }

  void _stopTracking() {
    _wsTrack?.close();
    _wsTrack = null;
    setState(() {});
  }

  Future<void> _setState(String state) async {
    setState(() => _loading = true);
    try {
      await _api.setDeliveryState(_deliveryId, state);
      if (mounted) setState(() {
        widget.mission['state'] = state;
        _loading = false;
      });
    } catch (e) {
      if (mounted) setState(() {
        _error = e.toString().replaceFirst('Exception: ', '');
        _loading = false;
      });
    }
  }

  Future<void> _deliverAndCollect() async {
    setState(() => _loading = true);
    try {
      await _api.collectPayment(_deliveryId, method: 'cash');
      await _api.setDeliveryState(_deliveryId, 'delivered');
      if (mounted) setState(() {
        widget.mission['state'] = 'delivered';
        _loading = false;
      });
    } catch (e) {
      if (mounted) setState(() {
        _error = e.toString().replaceFirst('Exception: ', '');
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final lat = _currentPosition?.latitude ?? 33.57;
    final lon = _currentPosition?.longitude ?? -7.59;
    final center = LatLng(lat, lon);

    return Scaffold(
      appBar: AppBar(
        title: Text('Delivery #$_deliveryId'),
        centerTitle: true,
      ),
      body: Column(
        children: [
          Card(
            margin: const EdgeInsets.all(12),
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(_customerName, style: Theme.of(context).textTheme.titleMedium),
                  Text(_address, style: Theme.of(context).textTheme.bodyMedium),
                  Text('State: $_state', style: Theme.of(context).textTheme.bodySmall),
                  if (_error != null)
                    Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error, fontSize: 12)),
                ],
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12),
            child: Row(
              children: [
                FilledButton(
                  onPressed: _loading ? null : () => _setState('en_route'),
                  child: const Text('Start'),
                ),
                const SizedBox(width: 8),
                FilledButton(
                  onPressed: _loading ? null : () => _setState('arrived'),
                  child: const Text('Arrive'),
                ),
                const SizedBox(width: 8),
                FilledButton(
                  onPressed: _loading ? null : _deliverAndCollect,
                  child: const Text('Deliver + Cash'),
                ),
              ],
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(12),
            child: _wsTrack?.isActive == true
                ? OutlinedButton.icon(
                    onPressed: _stopTracking,
                    icon: const Icon(Icons.stop),
                    label: const Text('Stop Tracking'),
                  )
                : FilledButton.icon(
                    onPressed: _startTracking,
                    icon: const Icon(Icons.location_on),
                    label: const Text('Start Tracking'),
                  ),
          ),
          Expanded(
            child: FlutterMap(
              mapController: _mapController,
              options: MapOptions(
                initialCenter: center,
                initialZoom: 14,
                onMapReady: () => _mapController.move(center, 14),
              ),
              children: [
                TileLayer(
                  urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                  userAgentPackageName: 'com.example.liv_driver_app',
                ),
                MarkerLayer(
                  markers: [
                    Marker(
                      point: center,
                      width: 40,
                      height: 40,
                      child: const Icon(Icons.person_pin_circle, color: Colors.blue, size: 40),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
