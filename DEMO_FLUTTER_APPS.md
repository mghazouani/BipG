# LIV Demo Flutter Apps

Two lean Flutter demo apps for the LIV POC backend (FastAPI + Odoo): **liv_client_app** (customer) and **liv_driver_app** (driver/courier). Both use **OpenStreetMap** (no Google Maps).

## Quick start

1. **Backend running**  
   From repo root:
   ```bash
   docker compose up -d
   ```
   FastAPI on port 8000, with `WS_SECRET` and (for driver) Odoo with at least one delivery for the driver.

2. **Config (emulator vs device)**  
   In each app, edit `lib/config.dart`:
   - **Android emulator**: `useAndroidEmulator = true`  
     → API/WS use `10.0.2.2:8000` (host machine).
   - **Real Android device**: `useAndroidEmulator = false` and set `_deviceHost` to your PC’s LAN IP (e.g. `192.168.1.10`).  
     Phone and PC must be on the same Wi‑Fi.

3. **Run**

   **Client (customer):**
   ```bash
   cd liv_client_app
   flutter pub get
   flutter run
   ```

   **Driver:**
   ```bash
   cd liv_driver_app
   flutter pub get
   flutter run
   ```

   Select the Android device or emulator when prompted.

## URL summary

| Context              | API_BASE_URL           | WS_BASE_URL            |
|---------------------|------------------------|-------------------------|
| Android emulator    | http://10.0.2.2:8000   | ws://10.0.2.2:8000      |
| Real device (LAN)   | http://&lt;LAN_IP&gt;:8000 | ws://&lt;LAN_IP&gt;:8000   |

Replace `<LAN_IP>` with your machine’s IP (e.g. `192.168.1.10`). Get it with `ipconfig` (Windows) or `ifconfig` / `ip addr` (Linux/macOS).

## Apps overview

- **liv_client_app**: Place order → track delivery. Screens: Order (POST /client/orders), Tracking (poll GET /deliveries, confirm + create-mission if needed, map with driver position).
- **liv_driver_app**: Load active mission → mission details + state buttons (Start/Arrive/Deliver+Cash) + “Start Tracking” WebSocket (GPS every 10s). Config: `driverId`, `wsSecret` (must match backend `WS_SECRET`).

See each app’s **README.md** for config, screens, and backend contract.

## Fix Flutter / Android issues

If `flutter doctor` shows **Android toolchain** or **license** problems:

1. **Accept Android licenses** (in a terminal where `flutter` works):
   ```bash
   flutter doctor --android-licenses
   ```
   Type `y` + Enter for each prompt.

2. **Install Android SDK Command-line Tools** (if missing):  
   Android Studio → **Settings** → **Android SDK** → **SDK Tools** → check **Android SDK Command-line Tools (latest)** → Apply.

Full steps and optional Visual Studio (Windows desktop) fix: **`scripts/fix_flutter_android.md`**.  
Quick run: `powershell -File scripts/fix_flutter_android.ps1` (from repo root, in a terminal where Flutter is in PATH).

---

## First-time setup

If the app was added manually (no `flutter create`), generate platform files once:

```bash
cd liv_client_app   # or liv_driver_app
flutter create .
```

Then restore or keep your `lib/` and `pubspec.yaml` as needed and run `flutter pub get` and `flutter run`.

## Requirements

- Flutter stable (3.x)
- Android SDK (emulator or device)
- Backend: FastAPI with endpoints and WebSocket as in each app’s README
