# LIV Client App (Customer demo)

Flutter demo app for customers: place order, then track delivery on a map (OpenStreetMap).

## Requirements

- Flutter stable (3.x)
- Android emulator or real Android device

## Config

Edit `lib/config.dart`:

- **Emulator**: `useAndroidEmulator = true` → uses `10.0.2.2:8000` (host from emulator).
- **Real device**: `useAndroidEmulator = false` and set `_deviceHost` to your PC's LAN IP (e.g. `192.168.1.10`). Ensure phone and PC are on the same Wi‑Fi.

## Run

```bash
cd liv_client_app
flutter pub get
flutter run
```

Pick the Android device/emulator when prompted.

## Screens

1. **Order** – Name, phone, address, qty. "Place Order" → `POST /client/orders`. Navigates to Tracking with `sale_order_id` and optional `delivery_id`.
2. **Tracking** – Polls every 2s. If no `delivery_id`, calls confirm + create-mission then stores it. Shows delivery state and driver position on map (from `redis_last` or `last_lat`/`last_lon`).

## Backend

Expects FastAPI at `API_BASE_URL` with:

- `POST /client/orders` – create order (returns `sale_order_id`, optional `delivery_id`)
- `POST /backoffice/orders/{id}/confirm`
- `POST /backoffice/orders/{id}/create-mission` – returns `delivery_id`
- `GET /deliveries/{id}` – delivery + `redis_last` / last position
