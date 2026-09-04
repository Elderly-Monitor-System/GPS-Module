# GPS-Module

## Elderly Outdoor Safety Monitoring System

GPS Software Prototype Version

Version: v0.1.0


---

# 1. Project Introduction


GPS-Module is the GPS positioning software module of the Elderly Outdoor Safety Monitoring System.


This version focuses on verifying the complete software workflow:


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


The current version completes the software prototype validation.


Hardware devices such as GPS module and ESP32 will be integrated in future versions.



---

# 2. Current Functions


## Backend


Implemented:


- FastAPI server

- GPS data upload interface

- Latest location query

- Today track query

- Historical track query

- Time-based GPS query

- Coordinate validation

- MySQL data storage



## Frontend


Implemented:


- Web map display

- Real-time location monitoring

- Today trajectory display

- Historical trajectory query

- Time point location query



---

# 3. Technology Stack


## Backend


Language:


```
Python 3.14.6
```


Framework:


```
FastAPI
```


Database driver:


```
mysql-connector-python
```



## Database


Database:


```
MySQL 8.0
```


Database name:


```
elder_monitor
```


Main table:


```
locations
```



## Frontend


Technology:


```
HTML

CSS

JavaScript

AMap JavaScript API
```



---

# 4. System Architecture



```
Future GPS Device

        |

        |

      ESP32

        |

        |

    HTTP POST

        ↓

 FastAPI Backend

        ↓

 MySQL Database

        ↓

 REST API

        ↓

 Web Frontend

        ↓

 Map Display

```



---

# 5. Backend API



## 5.1 Upload GPS Location



Method:


```
POST /location
```



Function:


Receive GPS positioning data and save into MySQL.



Request Example:


```json
{
    "device_id": "elder001",
    "longitude": 120.123,
    "latitude": 30.456
}
```



Response Example:


```json
{
    "message": "GPS上传成功",
    "id": 1,
    "device_id": "elder001",
    "longitude": 120.123,
    "latitude": 30.456
}
```



---


## 5.2 Get Latest Location



Method:


```
GET /location
```



Function:


Return the latest GPS location information.



Response Example:


```json
{
    "id":1,
    "device_id":"elder001",
    "longitude":120.123,
    "latitude":30.456,
    "timestamp":"2026-08-22 10:00:00"
}
```



---


## 5.3 Get Today Track



Method:


```
GET /locations/today
```



Function:


Query GPS trajectory data from today 00:00:00 to current time.



Response:


```json
{
    "device_id":"elder001",
    "date":"2026-08-22",
    "count":10,
    "locations":[]
}
```



---


## 5.4 Get Historical Track By Date



Method:


```
GET /locations/history/date
```



Parameter:


```
date_str=YYYY-MM-DD
```



Example:


```
/locations/history/date?date_str=2026-08-20
```



Function:


Query GPS trajectory according to specified date.



---


## 5.5 Get Location Near Specific Time



Method:


```
GET /locations/nearest
```



Parameters:


```
date_str

time_str
```



Example:


```
/locations/nearest?

date_str=2026-08-20

&time_str=14:30:00
```



Function:


Find the nearest GPS record within the specified time range.



---

# 6. Database Structure



Database:


```
elder_monitor
```



Table:


```
locations
```



Structure:


| Field | Type | Description |
|---|---|---|
| id | BIGINT | Primary key |
| device_id | VARCHAR | Device identifier |
| longitude | DOUBLE | Longitude |
| latitude | DOUBLE | Latitude |
| timestamp | DATETIME | Database recording time |



Description:


The current version uses MySQL generated timestamp.


Future hardware versions will introduce GPS acquisition time after GPS module integration.



---

# 7. Running Environment



Backend:


```
Python 3.14.6

FastAPI

Uvicorn

mysql-connector-python
```



Database:


```
MySQL 8.0
```



Frontend:


```
HTML

CSS

JavaScript

AMap JavaScript API
```



---

# 8. Project Structure



```
GPS-Module

│

├── backend

│   ├── main.py

│   └── requirements.txt

│

├── frontend

│   └── index.html

│

├── README.md

│

└── CHANGELOG.md

```



---

# 9. Current Development Status



## Completed


- [x] FastAPI backend

- [x] GPS upload interface

- [x] MySQL database storage

- [x] Real-time location query

- [x] Today trajectory query

- [x] Historical trajectory query

- [x] Time point GPS query

- [x] Web map visualization



---


## Not Included Yet



Future development:


- GPS hardware module

- ESP32 firmware

- Wireless communication

- Cloud server deployment



---

# 10. Development Roadmap



## v0.1.0


Software prototype validation version.


Completed:


- Backend service

- Database storage

- API interface

- Web visualization



---


## v0.2.0


Hardware integration version.


Plan:


- ESP32 connection

- GPS module communication

- Automatic positioning upload



---


## v0.3.0


Network deployment version.


Plan:


- Remote server

- 4G communication



---


## v1.0.0


Complete elderly outdoor safety monitoring system.



---

# 11. Security Notice



Before public deployment:


Do not upload:


- Database password

- API keys

- Private configuration files



Production deployment should use environment variables.



---

# 12. License



No license currently.



```
