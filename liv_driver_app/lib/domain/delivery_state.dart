/// Delivery state machine — Flutter source of truth.
///
/// Mirrors ALLOWED_TRANSITIONS in backend-fastapi/app/main.py.
/// Keep both in sync when adding states or transitions.

enum DeliveryState {
  draft,
  assigned,
  enRoute,
  arrived,
  delivered,
  cancelled;

  /// Parse a raw string from the API (e.g. "en_route" → [enRoute]).
  /// Returns [DeliveryState.draft] for unknown values.
  static DeliveryState fromApi(String? raw) => switch (raw) {
        'draft' => draft,
        'assigned' => assigned,
        'en_route' => enRoute,
        'arrived' => arrived,
        'delivered' => delivered,
        'cancelled' => cancelled,
        _ => draft,
      };

  /// The string value sent to / received from the API.
  String get apiValue => switch (this) {
        draft => 'draft',
        assigned => 'assigned',
        enRoute => 'en_route',
        arrived => 'arrived',
        delivered => 'delivered',
        cancelled => 'cancelled',
      };
}

/// Driver actions available from the mission screen.
enum DriverAction { start, arrive, deliver, cancel }

/// Returns the set of [DriverAction]s the driver may perform from [state].
///
/// Maps to the state machine transitions:
///   assigned  → en_route  (start)
///   assigned  → cancelled (cancel)   ← driver cancels before starting
///   en_route  → arrived   (arrive)
///   en_route  → delivered (deliver)
///   arrived   → delivered (deliver)
///
/// Cancel is intentionally restricted to [DeliveryState.assigned] only.
/// Once the driver has started (en_route) the mission should be escalated
/// to a backoffice operator rather than cancelled from the mobile app.
Set<DriverAction> allowedActions(DeliveryState state) => switch (state) {
      DeliveryState.assigned => {DriverAction.start, DriverAction.cancel},
      DeliveryState.enRoute => {DriverAction.arrive, DriverAction.deliver},
      DeliveryState.arrived => {DriverAction.deliver},
      _ => {},
    };
