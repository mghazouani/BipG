import 'package:flutter_test/flutter_test.dart';
import 'package:liv_driver_app/domain/delivery_state.dart';

void main() {
  group('DeliveryState.fromApi', () {
    test('parses known values', () {
      expect(DeliveryState.fromApi('draft'), DeliveryState.draft);
      expect(DeliveryState.fromApi('assigned'), DeliveryState.assigned);
      expect(DeliveryState.fromApi('en_route'), DeliveryState.enRoute);
      expect(DeliveryState.fromApi('arrived'), DeliveryState.arrived);
      expect(DeliveryState.fromApi('delivered'), DeliveryState.delivered);
      expect(DeliveryState.fromApi('cancelled'), DeliveryState.cancelled);
    });

    test('falls back to draft for unknown/null', () {
      expect(DeliveryState.fromApi(null), DeliveryState.draft);
      expect(DeliveryState.fromApi(''), DeliveryState.draft);
      expect(DeliveryState.fromApi('bogus'), DeliveryState.draft);
    });
  });

  group('DeliveryState.apiValue round-trip', () {
    for (final state in DeliveryState.values) {
      test('${state.name} → apiValue → fromApi', () {
        expect(DeliveryState.fromApi(state.apiValue), state);
      });
    }
  });

  group('allowedActions — states with actions', () {
    test('draft: no actions', () {
      expect(allowedActions(DeliveryState.draft), isEmpty);
    });

    test('assigned: start + cancel', () {
      expect(allowedActions(DeliveryState.assigned), {DriverAction.start, DriverAction.cancel});
    });

    test('en_route: arrive + deliver', () {
      expect(
        allowedActions(DeliveryState.enRoute),
        {DriverAction.arrive, DriverAction.deliver},
      );
    });

    test('arrived: deliver only', () {
      expect(allowedActions(DeliveryState.arrived), {DriverAction.deliver});
    });

    test('delivered: no actions', () {
      expect(allowedActions(DeliveryState.delivered), isEmpty);
    });

    test('cancelled: no actions', () {
      expect(allowedActions(DeliveryState.cancelled), isEmpty);
    });
  });

  group('allowedActions — action membership', () {
    test('start is only allowed from assigned', () {
      final statesWithStart = DeliveryState.values
          .where((s) => allowedActions(s).contains(DriverAction.start))
          .toList();
      expect(statesWithStart, [DeliveryState.assigned]);
    });

    test('arrive is only allowed from en_route', () {
      final statesWithArrive = DeliveryState.values
          .where((s) => allowedActions(s).contains(DriverAction.arrive))
          .toList();
      expect(statesWithArrive, [DeliveryState.enRoute]);
    });

    test('deliver is allowed from en_route and arrived', () {
      final statesWithDeliver = DeliveryState.values
          .where((s) => allowedActions(s).contains(DriverAction.deliver))
          .toSet();
      expect(statesWithDeliver, {DeliveryState.enRoute, DeliveryState.arrived});
    });

    test('cancel is only allowed from assigned', () {
      final statesWithCancel = DeliveryState.values
          .where((s) => allowedActions(s).contains(DriverAction.cancel))
          .toList();
      expect(statesWithCancel, [DeliveryState.assigned]);
    });

    test('cancel is NOT allowed from en_route, arrived, delivered, cancelled, draft', () {
      for (final s in [
        DeliveryState.draft,
        DeliveryState.enRoute,
        DeliveryState.arrived,
        DeliveryState.delivered,
        DeliveryState.cancelled,
      ]) {
        expect(
          allowedActions(s).contains(DriverAction.cancel),
          isFalse,
          reason: 'cancel should not be available from ${s.apiValue}',
        );
      }
    });
  });
}
