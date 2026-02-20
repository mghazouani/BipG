/// Widget tests: which buttons are visible for each delivery state.
///
/// Strategy: We test only the state-machine logic via unit tests in
/// delivery_state_test.dart, plus a lightweight render smoke test here
/// that verifies the correct buttons appear.
///
/// MissionScreen is network-heavy (maps, GPS), so we use a minimal
/// MaterialApp wrapper and skip map rendering by providing a
/// replacement widget via a test-only constructor. Instead of fully
/// mounting MissionScreen (which triggers flutter_map TileLayer HTTP),
/// we test the button visibility rule in isolation using a small helper
/// widget that replicates only the button-rendering logic.
library;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:liv_driver_app/domain/delivery_state.dart';

/// Minimal widget that mirrors the button-rendering logic of MissionScreen.
class _ButtonsUnderTest extends StatelessWidget {
  final DeliveryState state;
  const _ButtonsUnderTest(this.state);

  @override
  Widget build(BuildContext context) {
    final actions = allowedActions(state);

    if (actions.isEmpty) {
      return Text('no_actions:${state.apiValue}');
    }

    return Row(
      children: [
        if (actions.contains(DriverAction.start))
          const Text('btn:Start'),
        if (actions.contains(DriverAction.arrive))
          const Text('btn:Arrive'),
        if (actions.contains(DriverAction.deliver))
          const Text('btn:Deliver'),
      ],
    );
  }
}

Widget _wrap(DeliveryState state) => MaterialApp(
      home: Scaffold(body: _ButtonsUnderTest(state)),
    );

void main() {
  group('Button visibility per delivery state', () {
    testWidgets('draft → no buttons', (tester) async {
      await tester.pumpWidget(_wrap(DeliveryState.draft));
      expect(find.text('btn:Start'), findsNothing);
      expect(find.text('btn:Arrive'), findsNothing);
      expect(find.text('btn:Deliver'), findsNothing);
      expect(find.text('no_actions:draft'), findsOneWidget);
    });

    testWidgets('assigned → Start only', (tester) async {
      await tester.pumpWidget(_wrap(DeliveryState.assigned));
      expect(find.text('btn:Start'), findsOneWidget);
      expect(find.text('btn:Arrive'), findsNothing);
      expect(find.text('btn:Deliver'), findsNothing);
    });

    testWidgets('en_route → Arrive + Deliver, no Start', (tester) async {
      await tester.pumpWidget(_wrap(DeliveryState.enRoute));
      expect(find.text('btn:Start'), findsNothing);
      expect(find.text('btn:Arrive'), findsOneWidget);
      expect(find.text('btn:Deliver'), findsOneWidget);
    });

    testWidgets('arrived → Deliver only', (tester) async {
      await tester.pumpWidget(_wrap(DeliveryState.arrived));
      expect(find.text('btn:Start'), findsNothing);
      expect(find.text('btn:Arrive'), findsNothing);
      expect(find.text('btn:Deliver'), findsOneWidget);
    });

    testWidgets('delivered → no buttons', (tester) async {
      await tester.pumpWidget(_wrap(DeliveryState.delivered));
      expect(find.text('btn:Start'), findsNothing);
      expect(find.text('btn:Arrive'), findsNothing);
      expect(find.text('btn:Deliver'), findsNothing);
      expect(find.text('no_actions:delivered'), findsOneWidget);
    });

    testWidgets('cancelled → no buttons', (tester) async {
      await tester.pumpWidget(_wrap(DeliveryState.cancelled));
      expect(find.text('btn:Start'), findsNothing);
      expect(find.text('btn:Arrive'), findsNothing);
      expect(find.text('btn:Deliver'), findsNothing);
      expect(find.text('no_actions:cancelled'), findsOneWidget);
    });
  });
}
