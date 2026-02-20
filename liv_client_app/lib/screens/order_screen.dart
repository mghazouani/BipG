import 'package:flutter/material.dart';
import '../config.dart';
import '../services/api_service.dart';
import '../services/health_service.dart';
import 'tracking_screen.dart';

class OrderScreen extends StatefulWidget {
  const OrderScreen({super.key});

  @override
  State<OrderScreen> createState() => _OrderScreenState();
}

class _OrderScreenState extends State<OrderScreen> {
  final _formKey = GlobalKey<FormState>();
  final _name = TextEditingController(text: 'Demo Customer');
  final _phone = TextEditingController(text: '0600000000');
  final _address = TextEditingController(text: 'Casablanca');
  int _qty = 1;
  bool _loading = false;
  String? _error;

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

  @override
  void dispose() {
    _name.dispose();
    _phone.dispose();
    _address.dispose();
    super.dispose();
  }

  Future<void> _placeOrder() async {
    if (_loading) return;
    if (!(_formKey.currentState?.validate() ?? false)) return;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final data = await ApiService().placeOrder(
        customerName: _name.text.trim(),
        phone: _phone.text.trim(),
        address: _address.text.trim(),
        qty: _qty,
      );
      if (!mounted) return;
      final saleOrderId = data['sale_order_id'] as int? ?? data['id'] as int?;
      final deliveryId = data['delivery_id'] as int?;
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(
          builder: (_) => TrackingScreen(
            saleOrderId: saleOrderId!,
            deliveryId: deliveryId,
          ),
        ),
      );
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = e.toString().replaceFirst('Exception: ', '');
          _loading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Place order'),
        centerTitle: true,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              if (_error != null)
                Padding(
                  padding: const EdgeInsets.only(bottom: 16),
                  child: Card(
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
                ),
              TextFormField(
                controller: _name,
                decoration: const InputDecoration(
                  labelText: 'Name',
                  border: OutlineInputBorder(),
                ),
                validator: (v) =>
                    (v == null || v.trim().isEmpty) ? 'Required' : null,
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: _phone,
                decoration: const InputDecoration(
                  labelText: 'Phone',
                  border: OutlineInputBorder(),
                ),
                keyboardType: TextInputType.phone,
                validator: (v) =>
                    (v == null || v.trim().isEmpty) ? 'Required' : null,
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: _address,
                decoration: const InputDecoration(
                  labelText: 'Address',
                  border: OutlineInputBorder(),
                ),
                maxLines: 2,
                validator: (v) =>
                    (v == null || v.trim().isEmpty) ? 'Required' : null,
              ),
              const SizedBox(height: 16),
              DropdownButtonFormField<int>(
                initialValue: _qty,
                decoration: const InputDecoration(
                  labelText: 'Quantity',
                  border: OutlineInputBorder(),
                ),
                items: [1, 2, 3, 4, 5]
                    .map((e) => DropdownMenuItem(value: e, child: Text('$e')))
                    .toList(),
                onChanged: (v) => setState(() => _qty = v ?? 1),
              ),
              const SizedBox(height: 24),
              FilledButton(
                onPressed: _loading ? null : _placeOrder,
                child: _loading
                    ? const SizedBox(
                        height: 24,
                        width: 24,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Text('Place Order'),
              ),
              const SizedBox(height: 12),
              Text(
                'API: $apiBaseUrl',
                style: Theme.of(context).textTheme.bodySmall,
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 8),
              Center(
                child: _HealthBadge(
                  result: _health,
                  checking: _healthChecking,
                  onRefresh: _checkHealth,
                ),
              ),
            ],
          ),
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
        mainAxisSize: MainAxisSize.min,
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
