# GPS-Module · 老人GPS定位监护系统

> 基于 ESP32 + L80-R GPS 模块 + FastAPI + MySQL + 高德地图的老年人户外定位监护系统定位软件模块，本闭环系统作为在户外老人检测系统中的核心模块为完整系统提供，数据定位传输，本地化存储，后端算法运行，前端高德界面的交互展示和结构设计，会在后续的测试和实际应用中不断优化交互体验和数据处理方式。

**当前版本：v2.0.0**（真实硬件联调版）

| 版本 | 说明 | 标签 |
| --- | --- | --- |
| v0.1.0 | 纯软件原型：FastAPI + MySQL + 网页地图 | `v0.1.0` |
| v2.0.0 | ESP32 + L80-R 真实硬件接入、GPS 时间体系、坐标转换 | `v2.0.0` |

---

## 1. 项目简介

本项目是"老人户外安全监护装置"的 GPS 定位软件模块。v2.0.0 已打通真实硬件链路：

```
L80-R GPS 模块（WGS84 + GPS UTC 时间）
        ↓ UART 9600 / GPIO14
ESP32 固件（GPS_MONITOR 手机诊断热点 + 自动上传）
        ↓ HTTP POST /location（WiFi）
FastAPI 后端（UTC → 北京时间、轨迹抽稀、数据校验）
        ↓ mysql-connector
MySQL 8.0（elder_monitor.locations）
        ↓ REST API（同源相对路径）
Web 前端（高德地图，WGS84 → GCJ-02 展示转换）
        ↓
实时定位 / 今日轨迹 / 历史轨迹 / 指定时刻查询
```

## 2. 仓库结构

```
GPS-Module
├── firmware/
│   └── esp32_l80r_gps.ino   # ESP32 + L80-R 增强版固件（含手机诊断热点）
├── backend/
│   ├── main.py              # FastAPI 后端（v2.0）
│   └── requirements.txt     # Python 依赖
├── frontend/
│   └── index.html           # Web 前端（单文件，高德地图）
├── database/
│   └── schema.sql           # 建库建表脚本 + v0.1.0 旧库迁移 SQL
├── docs/
│   ├── technical-roadmap.md # 技术路线 V7.0（架构、实施记录、故障复盘、复现指南）
│   └── hardware-setup.md    # 固件 v4.0 烧录与手机诊断使用手册
├── README.md
└── CHANGELOG.md
```

## 3. 功能特性

**ESP32 固件**
- TinyGPSPlus 持续解析 NMEA，仅上传新的有效 GPS Fix（含新鲜度、去重判断）
- GPS UTC 时间以 ISO 8601 上传（`2026-08-28T01:55:30Z`），北京时间转换统一由后端完成
- `GPS_MONITOR` AP 手机诊断热点（`http://192.168.4.1`），无需串口监视器即可查看 UART / 搜星 / Fix / 上传状态
- WiFi 断线自动重连、HTTP 2xx 才确认上传成功、GPS 串口健康自检

**FastAPI 后端**
- `gps_time`（GPS 实际定位时间）与 `received_at`（服务器接收时间）双时间体系
- `POST /location` 时区校验、坐标校验、device_id 校验，多设备预留
- 今日 / 指定日期 / 自定义范围 / 指定时刻（±5 分钟）轨迹查询，50 米阈值轨迹抽稀（Haversine）
- 数据库配置全部走环境变量，密码不写死在代码中
- 直接托管前端静态文件，浏览器统一访问 8000 端口

**Web 前端**
- 2 秒轮询实时定位 + 今日轨迹 + 历史轨迹 + 指定时刻查询
- 全部覆盖物绘制前统一 WGS84 → GCJ-02 转换（数据库始终保存原始 WGS84）
- 日期统一按北京时间（UTC+8）计算，与浏览器时区无关
- 无数据 / 错误 detail 等异常状态友好处理

## 4. 快速开始

### 4.1 后端 + 数据库

```powershell
# 1. 初始化数据库（MySQL 8.0）
mysql -u root -p < database/schema.sql

# 2. 设置数据库密码环境变量（只对当前终端生效）
$env:DB_PASSWORD="你的MySQL密码"
# 可选：$env:DB_HOST / DB_PORT / DB_USER / DB_NAME（默认 127.0.0.1 / 3306 / root / elder_monitor）

# 3. 安装依赖并启动后端
cd backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

访问 `http://127.0.0.1:8000/`（前端页面）、`http://127.0.0.1:8000/docs`（Swagger API 文档）、`http://127.0.0.1:8000/api/health`（健康检查）。

### 4.2 ESP32 固件烧录

1. Arduino IDE 安装开发板 **ESP32**，库管理器安装 **TinyGPSPlus**。
2. 打开 `firmware/esp32_l80r_gps.ino`，替换以下占位符（**见第 5 节安全说明**）：
   - `YOUR_WIFI_SSID` / `YOUR_WIFI_PASSWORD`：主 WiFi（手机热点）名称与密码
   - `YOUR_SERVER_IP`：运行 FastAPI 的电脑局域网 IPv4
3. 接线（经本项目实测确认，勿按普通模块丝印方向推断）：

   | GPS 小板 | ESP32 | 说明 |
   | --- | --- | --- |
   | RX（丝印） | GPIO14 | **实测为 GPS 数据输出脚**，接 ESP32 RX |
   | TX（丝印） | GPIO13 | 本项目不需要 ESP32 向 GPS 发命令时可暂不接 |
   | VCC | 3.3V | ESP32 3.3V 供电 |
   | GND | GND | 必须可靠共地 |

4. 选择 ESP32-WROVER-DEV 开发板，波特率 115200 烧录。
5. 烧录后手机可连接 `GPS_MONITOR`（密码 `12345678`），浏览器打开 `http://192.168.4.1` 查看实时诊断。

详细烧录、排障与测试方法见 [`docs/hardware-setup.md`](docs/hardware-setup.md)。

## 5. 安全说明（重要）

仓库中所有敏感配置均已占位符化，提交前请勿填入真实值：

| 占位符 | 位置 | 对应内容 |
| --- | --- | --- |
| `YOUR_WIFI_SSID` / `YOUR_WIFI_PASSWORD` | 固件 | 主 WiFi 凭据 |
| `YOUR_SERVER_IP` | 固件 | FastAPI 服务器局域网 IP |
| `YOUR_AMAP_KEY` / `YOUR_AMAP_SECURITY_CODE` | 前端 | 高德地图 JS API Key 与安全密钥 |
| `DB_PASSWORD` 环境变量 | 后端 | MySQL 密码 |

建议：
- 曾经出现在旧版文档/截图中的 WiFi 密码、数据库密码、高德 Key 应尽快**轮换**。
- 高德 Key 在控制台设置**域名白名单**，防止被盗用。
- 公网部署前需补充 HTTPS、设备鉴权与 API 幂等（见技术路线文档阶段 7）。

## 6. 后端 API 一览

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/` | 返回前端页面（FastAPI 托管） |
| GET | `/api/health` | 后端健康检查 |
| POST | `/location` | ESP32 上传定位（`device_id` + `longitude` + `latitude` + `gps_time`） |
| GET | `/location?device_id=elder001` | 获取设备最新定位 |
| GET | `/locations/today?device_id=elder001` | 今日轨迹 |
| GET | `/locations/history/date?date_str=YYYY-MM-DD` | 指定日期历史轨迹 |
| GET | `/locations/history/range?start_time=...&end_time=...` | 自定义时间范围轨迹 |
| GET | `/locations/nearest?date_str=...&time_str=HH:MM:SS` | 指定时刻前后 5 分钟最近定位 |

POST 请求示例：

```json
{
  "device_id": "elder001",
  "longitude": 116.123456,
  "latitude": 39.123456,
  "gps_time": "2026-08-28T01:55:30Z"
}
```

## 7. 数据库

数据库 `elder_monitor`，主表 `locations`：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | BIGINT | 主键 |
| device_id | VARCHAR(64) | 设备标识（默认 elder001，预留多设备） |
| longitude | DOUBLE | 经度（WGS84 原始值） |
| latitude | DOUBLE | 纬度（WGS84 原始值） |
| gps_time | DATETIME | GPS 实际定位时间（北京时间） |
| received_at | DATETIME | 服务器接收写入时间 |

联合索引：`(device_id, gps_time)`。完整脚本与旧库迁移 SQL 见 [`database/schema.sql`](database/schema.sql)。

## 8. 项目文档

- [`docs/technical-roadmap.md`](docs/technical-roadmap.md) — 技术路线 V7.0：系统架构、实施记录、故障复盘、从零复现指南、后续开发计划
- [`docs/hardware-setup.md`](docs/hardware-setup.md) — 固件 v4.0 烧录、接线与手机诊断使用手册
- [`CHANGELOG.md`](CHANGELOG.md) — 版本变更记录

## 9. 当前状态与后续计划

**已完成**：L80-R → ESP32 → WiFi → FastAPI → MySQL → Web 高德地图的真实硬件阶段性联调。

**尚未最终验收**：真实 GPS 定位质量与 24 小时连续运行测试、独立供电、断网缓存补传、`gps_time` 全链路切换、公网/4G 部署、SOS/跌倒检测等安全监护扩展。详见技术路线文档第 7、8 章。

## 10. 许可证

暂无许可证。
