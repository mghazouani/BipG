# LIV Driver App (Courier demo)

Flutter demo app for drivers: load active mission, update state, send GPS via WebSocket every 10s (OpenStreetMap).

## Requirements

- Flutter stable (3.x)
- Android emulator or real device
- Backend with `WS_SECRET` matching `lib/config.dart` (`wsSecret`)

## Config

Edit `lib/config.dart`:

- **Emulator**: `useAndroidEmulator = true` → `10.0.2.2:8000`
- **Real device**: `useAndroidEmulator = false` and set `_deviceHost` to your PC LAN IP (e.g. `192.168.1.10`)
- `driverId`: Odoo user ID for this driver (default 2)
- `wsSecret`: must match backend `WS_SECRET` for token generation

## Run

```bash
cd liv_driver_app
flutter pub get
flutter run
```

## Screens

1. **Driver Home** – Shows driver ID. "Load Active Mission" → `GET /drivers/{id}/active-mission`. If mission exists, navigate to Mission.
2. **Mission** – Delivery id, customer, address, state. Buttons: Start (en_route), Arrive (arrived), Deliver + Collect Cash (collect-payment + delivered). "Start Tracking" opens WebSocket, sends GPS every 10s; "Stop Tracking" closes it. Map shows current driver position.

## Backend

- `GET /drivers/{driver_id}/active-mission`
- `POST /deliveries/{id}/state` body `{"state": "..."}`
- `POST /deliveries/{id}/collect-payment` body `{"method":"cash", ...}`
- `WS /ws/track?token=<token>` – token = base64(driver_id:delivery_id:timestamp:signature), HMAC-SHA256 with WS_SECRET. Send JSON: delivery_id, driver_id, lat, lon, ts, optional speed/heading. Rate limit: 1 msg per 10s.

## Permissions

Android: location (for geolocator). Add in `AndroidManifest.xml` if not present:

- `ACCESS_FINE_LOCATION`
- `ACCESS_COARSE_LOCATION`
