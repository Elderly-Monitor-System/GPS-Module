# Changelog

All notable changes to this project will be documented in this file.

# v2.0.0

Release Date:

2026-09-21

## Overview

Second major release: real hardware integration.

The complete chain `L80-R GPS → ESP32 → WiFi → FastAPI → MySQL → Web (AMap)` has been verified through real device testing. This release upgrades the v0.1.0 software prototype into a hardware-connected system with a unified GPS time system and correct map coordinate handling.

Compared to v0.1.0, the intermediate local iterations (v5.0/v6.0/v7.0 document baselines) are consolidated into this release.

## Added

### Firmware (new)

- ESP32 + L80-R enhanced firmware (`firmware/esp32_l80r_gps.ino`)
- TinyGPSPlus NMEA parsing with continuous capture of new valid GPS fixes
- `GPS_MONITOR` AP phone diagnostics hotspot (`http://192.168.4.1`)
- Upload freshness control, dedup by GPS time, HTTP 2xx success confirmation
- WiFi auto-reconnect and GPS serial health check
- All credentials replaced with placeholders (`YOUR_WIFI_SSID` / `YOUR_SERVER_IP`)

### Backend

- `gps_time` (GPS fix time) and `received_at` (server receive time) dual time system
- GPS UTC → Beijing time (UTC+8) conversion with timezone validation
- `device_id` query support with `elder001` default for future multi-device
- Track simplification (Haversine, 50 m threshold, first/last point preserved)
- `GET /locations/history/range` custom time range query
- FastAPI serves frontend static files (`GET /`), health check moved to `GET /api/health`
- Database config from environment variables (password never hardcoded)
- Removed duplicate function/route definitions from v0.1.0 code

### Frontend

- All API calls use relative paths (works from LAN and localhost)
- WGS84 → GCJ-02 conversion before all AMap Marker/Polyline rendering
- `gps_time` display in location info card
- Beijing time (UTC+8) date utilities for today/yesterday/N-days-ago
- Time input auto-pads to HH:MM:SS for `/locations/nearest`
- Friendly handling of `found=false`, invalid coordinates, and API error details

### Database

- `database/schema.sql` with full table definition and `(device_id, gps_time)` index
- Migration SQL for v0.1.0 databases (rename `timestamp` → `received_at`, add `gps_time`)

### Docs

- `docs/technical-roadmap.md` — technical roadmap V7.0 (architecture, implementation records, troubleshooting, reproduction guide)
- `docs/hardware-setup.md` — firmware v4.0 flashing, wiring and phone diagnostics manual
- Rewritten README with quick start, API reference, hardware wiring table, security notes
- `.gitignore`

## Security

- All real credentials (WiFi password, AMap keys, LAN IP) replaced with placeholders
- Users must rotate credentials that appeared in earlier local documents

## Known Limitations

- Real GPS positioning quality and 24h continuous run not yet fully validated
- WGS84 coordinates stored raw; GCJ-02 conversion is display-layer only
- No offline cache / retry upload on firmware yet
- No public deployment (4G/HTTPS/device auth) yet

---

# v0.1.0

Release Date:

2026-08-22

## Overview

Initial software prototype release of GPS-Module.

This version verifies the complete GPS positioning software workflow:

```
GPS Data
↓
FastAPI Backend
↓
MySQL Database
↓
Web Frontend
↓
Map Visualization
```

---

# Added

## Backend

- FastAPI application framework
- GPS location upload interface
- Latest location query interface
- Today trajectory query
- Historical trajectory query
- Time point GPS query
- Coordinate validation
- MySQL database connection

## Frontend

- Web map monitoring interface
- Real-time positioning display
- Today trajectory visualization
- Historical trajectory visualization
- Time point location query

## Database

- MySQL database support
- Location data storage table

---

# API Added

## Upload Location

```
POST /location
```

## Latest Location

```
GET /location
```

## Today Track

```
GET /locations/today
```

## Historical Track

```
GET /locations/history/date
```

## Time Query

```
GET /locations/nearest
```

---

# Known Limitations

## Hardware

Not included:

- GPS hardware module
- ESP32 firmware
- Wireless communication module

## Deployment

Not included:

- Cloud server deployment
- Remote access
- User management

## Time Information

Current version uses:

```
MySQL timestamp
```

Future versions will integrate:

```
GPS acquisition time
```
