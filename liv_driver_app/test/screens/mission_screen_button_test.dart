/// Widget tests: which buttons are visible for each delivery state,
/// including the Cancel button (S3) and its confirmation dialog.
///
/// Strategy: MissionScreen is network-heavy (maps, GPS), so we test the
/// button-rendering and dialog logic in isolation using a small helper
/// widget that replicates only the relevant UI behaviour.
library;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:liv_driver_app/domain/delivery_state.dart';
import 'package:liv_driver_app/services/api_service.dart';

// ---------------------------------------------------------------------------
// Test helper widget — mirrors MissionScreen button + cancel logic
// ---------------------------------------------------------------------------

class _MissionButtonsUnderTest extends StatefulWidget {
  final DeliveryState initialState;
  /// If set, performing cancel will throw this exception (simulates 422).
  final Exception? cancelException;

  const _MissionButtonsUnderTest({
    required this.initialState,
    this.cancelException,
  });

  @override
  State<_MissionButtonsUnderTest> createState() => _MissionButtonsUnderTestState();
}

class _MissionButtonsUnderTestState extends State<_MissionButtonsUnderTest> {
  late DeliveryState _state;
  String? _error;

  @override
  void initState() {
    super.initState();
    _state = widget.initialState;
  }

  Future<bool> _confirmCancel() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Cancel mission?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('Keep'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(ctx).pop(true),
            child: const Text('Cancel mission'),
          ),
        ],
      ),
    );
    return confirmed ?? false;
  }

  Future<void> _performAction(DriverAction action) async {
    if (action == DriverAction.cancel) {
      final confirmed = await _confirmCancel();
      if (!confirmed) return;
    }
    try {
      if (widget.cancelException != null && action == DriverAction.cancel) {
        throw widget.cancelException!;
      }
      final next = switch (action) {
        DriverAction.start  => DeliveryState.enRoute,
        DriverAction.arrive => DeliveryState.arrived,
        DriverAction.deliver => DeliveryState.delivered,
        DriverAction.cancel => DeliveryState.cancelled,
      };
      setState(() { _state = next; _error = null; });
    } catch (e) {
      setState(() => _error = e.toString());
    }
  }

  @override
  Widget build(BuildContext context) {
    final actions = allowedActions(_state);
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('state:${_state.apiValue}'),
        if (_error != null) Text('error:$_error'),
        Row(
          children: [
            if (actions.contains(DriverAction.start))
              TextButton(
                onPressed: () => _performAction(DriverAction.start),
                child: const Text('btn:Start'),
              ),
            if (actions.contains(DriverAction.arrive))
              TextButton(
                onPressed: () => _performAction(DriverAction.arrive),
                child: const Text('btn:Arrive'),
              ),
            if (actions.contains(DriverAction.deliver))
              TextButton(
                onPressed: () => _performAction(DriverAction.deliver),
                child: const Text('btn:Deliver'),
              ),
          ],
        ),
        if (actions.contains(DriverAction.cancel))
          TextButton(
            onPressed: () => _performAction(DriverAction.cancel),
            child: const Text('btn:Cancel'),
          ),
      ],
    );
  }
}

Widget _wrap(DeliveryState state, {Exception? cancelException}) => MaterialApp(
      home: Scaffold(
        body: _MissionButtonsUnderTest(
          initialState: state,
          cancelException: cancelException,
        ),
      ),
    );

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

void main() {
  group('Button visibility per delivery state', () {
    testWidgets('draft → no action buttons', (tester) async {
      await tester.pumpWidget(_wrap(DeliveryState.draft));
      expect(find.text('btn:Start'), findsNothing);
      expect(find.text('btn:Arrive'), findsNothing);
      expect(find.text('btn:Deliver'), findsNothing);
      expect(find.text('btn:Cancel'), findsNothing);
    });

    testWidgets('assigned → Start + Cancel, no Arrive/Deliver', (tester) async {
      await tester.pumpWidget(_wrap(DeliveryState.assigned));
      expect(find.text('btn:Start'), findsOneWidget);
      expect(find.text('btn:Cancel'), findsOneWidget);
      expect(find.text('btn:Arrive'), findsNothing);
      expect(find.text('btn:Deliver'), findsNothing);
    });

    testWidgets('en_route → Arrive + Deliver, no Start/Cancel', (tester) async {
      await tester.pumpWidget(_wrap(DeliveryState.enRoute));
      expect(find.text('btn:Start'), findsNothing);
      expect(find.text('btn:Arrive'), findsOneWidget);
      expect(find.text('btn:Deliver'), findsOneWidget);
      expect(find.text('btn:Cancel'), findsNothing);
    });

    testWidgets('arrived → Deliver only, no Cancel', (tester) async {
      await tester.pumpWidget(_wrap(DeliveryState.arrived));
      expect(find.text('btn:Start'), findsNothing);
      expect(find.text('btn:Arrive'), findsNothing);
      expect(find.text('btn:Deliver'), findsOneWidget);
      expect(find.text('btn:Cancel'), findsNothing);
    });

    testWidgets('delivered → no buttons', (tester) async {
      await tester.pumpWidget(_wrap(DeliveryState.delivered));
      expect(find.text('btn:Start'), findsNothing);
      expect(find.text('btn:Arrive'), findsNothing);
      expect(find.text('btn:Deliver'), findsNothing);
      expect(find.text('btn:Cancel'), findsNothing);
    });

    testWidgets('cancelled → no buttons', (tester) async {
      await tester.pumpWidget(_wrap(DeliveryState.cancelled));
      expect(find.text('btn:Start'), findsNothing);
      expect(find.text('btn:Arrive'), findsNothing);
      expect(find.text('btn:Deliver'), findsNothing);
      expect(find.text('btn:Cancel'), findsNothing);
    });
  });

  group('Cancel — confirmation dialog', () {
    testWidgets('tapping Cancel shows confirmation dialog', (tester) async {
      await tester.pumpWidget(_wrap(DeliveryState.assigned));

      await tester.tap(find.text('btn:Cancel'));
      await tester.pumpAndSettle();

      expect(find.text('Cancel mission?'), findsOneWidget);
      expect(find.text('Keep'), findsOneWidget);
      expect(find.text('Cancel mission'), findsWidgets); // button label
    });

    testWidgets('tapping Keep dismisses dialog without state change', (tester) async {
      await tester.pumpWidget(_wrap(DeliveryState.assigned));

      await tester.tap(find.text('btn:Cancel'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Keep'));
      await tester.pumpAndSettle();

      // State unchanged, dialog gone, cancel button still present
      expect(find.text('state:assigned'), findsOneWidget);
      expect(find.text('Cancel mission?'), findsNothing);
      expect(find.text('btn:Cancel'), findsOneWidget);
    });

    testWidgets('confirming Cancel changes state to cancelled', (tester) async {
      await tester.pumpWidget(_wrap(DeliveryState.assigned));

      await tester.tap(find.text('btn:Cancel'));
      await tester.pumpAndSettle();
      // Tap the "Cancel mission" button inside the dialog
      await tester.tap(find.widgetWithText(FilledButton, 'Cancel mission'));
      await tester.pumpAndSettle();

      expect(find.text('state:cancelled'), findsOneWidget);
      expect(find.text('Cancel mission?'), findsNothing);
      // No more action buttons in cancelled state
      expect(find.text('btn:Cancel'), findsNothing);
      expect(find.text('btn:Start'), findsNothing);
    });
  });

  group('Cancel — 422 handling', () {
    testWidgets('InvalidTransitionException shows error message', (tester) async {
      const ex = InvalidTransitionException("Cannot go from 'assigned' to 'cancelled'");
      await tester.pumpWidget(_wrap(DeliveryState.assigned, cancelException: ex));

      await tester.tap(find.text('btn:Cancel'));
      await tester.pumpAndSettle();
      await tester.tap(find.widgetWithText(FilledButton, 'Cancel mission'));
      await tester.pumpAndSettle();

      expect(find.textContaining("Cannot go from"), findsOneWidget);
      // State stays assigned after 422 — error shown, Cancel button still present.
      // In the real app _refreshMission() re-reads from the server; the stub
      // keeps the local state unchanged (assigned), so Cancel remains visible.
      expect(find.text('state:assigned'), findsOneWidget);
      expect(find.text('btn:Cancel'), findsOneWidget);
    });
  });
}
