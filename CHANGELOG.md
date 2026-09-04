# Changelog


All notable changes to this project will be documented in this file.



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



---


# Future Plan



## v0.2.0


Hardware integration:


- ESP32 communication

- GPS module data acquisition

- Automatic location upload



## v0.3.0


Network upgrade:


- Remote server

- 4G communication



## v1.0.0


Complete elderly outdoor safety monitoring system.

