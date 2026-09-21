from datetime import datetime, time, timedelta, timezone
from pathlib import Path
import os
 
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import mysql.connector
 
 
# ==================================================
# 基础配置
# ==================================================
 
BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR.parent / "frontend"
 
DEFAULT_DEVICE_ID = "elder001"
TRACK_DISTANCE_THRESHOLD = 50  # 轨迹抽稀阈值，单位：米
NEAREST_MAX_DIFF_MINUTES = 5   # 指定时刻查询前后范围，单位：分钟
 
# 数据库存储 gps_time 时，统一保存为北京时间（UTC+8）的“无时区 DATETIME”
BEIJING_TZ = timezone(timedelta(hours=8))
 
# 数据库配置：建议通过环境变量设置，尤其不要把密码长期写死在 main.py 中
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "elder_monitor")
 
 
# ==================================================
# 创建 FastAPI 应用
# ==================================================
 
app = FastAPI(
    title="老人GPS定位监护系统",
    description="老人实时定位、今日轨迹、历史轨迹、指定时间附近定位查询",
    version="2.0",
)
 
 
# ==================================================
# CORS
#
# 正式使用 FastAPI 托管前端后，浏览器与后端同源，通常不需要 CORS。
# 这里仍保留 5500 端口，方便你临时用 Live Server 调试前端。
# ==================================================
 
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
 
 
# ==================================================
# FastAPI 托管前端静态文件
#
# 按你当前真实目录：
# GPS/
# ├── backend/
# │   └── main.py
# └── frontend/
#     ├── index.html
#     ├── app.js      （以后如果拆分）
#     └── style.css   （以后如果拆分）
#
# BASE_DIR 指向 GPS/backend；
# BASE_DIR.parent 指向 GPS；
# 再进入 frontend，即可找到前端目录。
# ==================================================
 
if FRONTEND_DIR.exists():
    app.mount(
        "/static",
        StaticFiles(directory=str(FRONTEND_DIR)),
        name="static",
    )
 
 
@app.get("/", include_in_schema=False)
def index():
    index_file = FRONTEND_DIR / "index.html"
 
    if not index_file.exists():
        raise HTTPException(
            status_code=500,
            detail="未找到 frontend/index.html，请检查 GPS/frontend/index.html 是否存在",
        )
 
    return FileResponse(str(index_file))
 
 
@app.get("/api/health")
def health_check():
    """后端存活测试接口。"""
    return {
        "message": "老人GPS定位监护系统运行正常",
        "server_time": datetime.now(BEIJING_TZ).strftime("%Y-%m-%d %H:%M:%S"),
    }
 
 
# ==================================================
# 数据库连接
# ==================================================
 
def get_db_connection():
    return mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset="utf8mb4",
    )
 
 
# ==================================================
# 定位上传数据模型
#
# gps_time 示例：
# 2026-08-28T01:55:30Z
#
# ESP32 上传 GPS 模块给出的 UTC 时间；
# FastAPI 负责转换为北京时间后写入 MySQL。
# ==================================================
 
class LocationData(BaseModel):
    device_id: str
    longitude: float
    latitude: float
    gps_time: datetime
 
 
# ==================================================
# 公共校验 / 时间处理
# ==================================================
 
def check_device_id(device_id: str) -> str:
    device_id = device_id.strip()
 
    if not device_id:
        raise HTTPException(
            status_code=400,
            detail="device_id不能为空",
        )
 
    return device_id
 
 
def check_coordinate(longitude: float, latitude: float):
    if not (-180 <= longitude <= 180):
        raise HTTPException(
            status_code=400,
            detail="经度范围错误，应在 -180 到 180 之间",
        )
 
    if not (-90 <= latitude <= 90):
        raise HTTPException(
            status_code=400,
            detail="纬度范围错误，应在 -90 到 90 之间",
        )
 
 
def gps_time_to_beijing(gps_time: datetime) -> datetime:
    """
    将 ESP32 上传的带时区 GPS 时间转换为北京时间。
 
    数据库使用 DATETIME，因此最终去掉 tzinfo 后保存。
    注意：必须同时处理日期跨天，不能只简单给小时 +8。
    """
    if gps_time.tzinfo is None or gps_time.utcoffset() is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "gps_time必须包含时区。"
                "推荐ESP32上传UTC格式，例如 2026-08-28T01:55:30Z"
            ),
        )
 
    beijing_time = gps_time.astimezone(BEIJING_TZ)
 
    return beijing_time.replace(
        tzinfo=None,
        microsecond=0,
    )
 
 
def normalize_query_datetime(value: datetime) -> datetime:
    """
    查询接口的 datetime：
    - 如果调用方传了时区，则转换为北京时间；
    - 如果没传时区，则按北京时间理解。
    数据库中的 gps_time 是北京时间无时区 DATETIME。
    """
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(microsecond=0)
 
    return value.astimezone(BEIJING_TZ).replace(
        tzinfo=None,
        microsecond=0,
    )
 
 
def format_datetime(value):
    if value is None:
        return None
 
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
 
    return str(value)
 
 
# ==================================================
# 数据行转换
#
# timestamp 为临时兼容字段：
# 旧前端若仍读取 timestamp，可以继续工作；
# 其值现在等于真正的 gps_time。
# ==================================================
 
def row_to_location(row):
    return {
        "id": row[0],
        "device_id": row[1],
        "longitude": float(row[2]),
        "latitude": float(row[3]),
        "gps_time": format_datetime(row[4]),
        "received_at": format_datetime(row[5]),
        "timestamp": format_datetime(row[4]),
    }
 
 
# ==================================================
# GET /location
# 获取某台设备最新实时定位
#
# 关键修改：
# 1. 按 device_id 查询，避免未来多设备串数据；
# 2. 按 gps_time DESC 排序，而不是按 id DESC；
# 3. id 作为相同 gps_time 时的第二排序条件。
# ==================================================
 
@app.get("/location")
def get_location(
    device_id: str = DEFAULT_DEVICE_ID,
):
    device_id = check_device_id(device_id)
 
    conn = None
    cursor = None
 
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
 
        sql = """
        SELECT
            id,
            device_id,
            longitude,
            latitude,
            gps_time,
            received_at
        FROM locations
        WHERE device_id = %s
        ORDER BY gps_time DESC, id DESC
        LIMIT 1
        """
 
        cursor.execute(sql, (device_id,))
        row = cursor.fetchone()
 
        if row is None:
            return {
                "found": False,
                "device_id": device_id,
                "message": "该设备暂无GPS数据",
            }
 
        result = row_to_location(row)
        result["found"] = True
        return result
 
    except mysql.connector.Error as e:
        raise HTTPException(
            status_code=500,
            detail=f"数据库读取失败: {str(e)}",
        )
 
    finally:
        if cursor:
            cursor.close()
 
        if conn and conn.is_connected():
            conn.close()
 
 
# ==================================================
# POST /location
# ESP32 上传新的 GPS 定位
#
# timestamp 不再作为业务定位时间。
# gps_time：GPS实际定位时间（FastAPI转北京时间）
# received_at：MySQL实际收到并写入的时间（数据库自动生成）
# ==================================================
 
@app.post("/location")
def upload_location(data: LocationData):
    device_id = check_device_id(data.device_id)
 
    check_coordinate(
        data.longitude,
        data.latitude,
    )
 
    gps_time_beijing = gps_time_to_beijing(data.gps_time)
 
    conn = None
    cursor = None
 
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
 
        sql = """
        INSERT INTO locations
        (
            device_id,
            longitude,
            latitude,
            gps_time
        )
        VALUES
        (
            %s,
            %s,
            %s,
            %s
        )
        """
 
        cursor.execute(
            sql,
            (
                device_id,
                data.longitude,
                data.latitude,
                gps_time_beijing,
            ),
        )
 
        conn.commit()
 
        return {
            "message": "GPS上传成功",
            "id": cursor.lastrowid,
            "device_id": device_id,
            "longitude": data.longitude,
            "latitude": data.latitude,
            "gps_time": format_datetime(gps_time_beijing),
        }
 
    except mysql.connector.Error as e:
        if conn:
            conn.rollback()
 
        raise HTTPException(
            status_code=500,
            detail=f"数据库写入失败: {str(e)}",
        )
 
    finally:
        if cursor:
            cursor.close()
 
        if conn and conn.is_connected():
            conn.close()
 
 
# ==================================================
# GPS 两点距离计算
# Haversine 公式，返回米
# ==================================================
 
def calculate_distance(
    lon1: float,
    lat1: float,
    lon2: float,
    lat2: float,
) -> float:
    import math
 
    earth_radius = 6371000
 
    rad_lat1 = math.radians(lat1)
    rad_lat2 = math.radians(lat2)
 
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
 
    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(rad_lat1)
        * math.cos(rad_lat2)
        * math.sin(delta_lon / 2) ** 2
    )
 
    c = 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a),
    )
 
    return earth_radius * c
 
 
# ==================================================
# GPS 轨迹自动抽稀
#
# 相邻两个“保留点”距离达到阈值才保留；
# 第一个点和最后一个点始终保留。
# ==================================================
 
def simplify_track(
    locations: list,
    distance_threshold: float = TRACK_DISTANCE_THRESHOLD,
):
    if len(locations) <= 2:
        return locations
 
    result = [locations[0]]
    last_point = locations[0]
 
    for point in locations[1:]:
        distance = calculate_distance(
            last_point["longitude"],
            last_point["latitude"],
            point["longitude"],
            point["latitude"],
        )
 
        if distance >= distance_threshold:
            result.append(point)
            last_point = point
 
    if result[-1]["id"] != locations[-1]["id"]:
        result.append(locations[-1])
 
    return result
 
 
# ==================================================
# 数据库查询轨迹公共函数
#
# 全部按 gps_time 查询、排序。
# ==================================================
 
def query_track_range(
    device_id: str,
    start_time: datetime,
    end_time: datetime,
):
    conn = None
    cursor = None
 
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
 
        sql = """
        SELECT
            id,
            device_id,
            longitude,
            latitude,
            gps_time,
            received_at
        FROM locations
        WHERE
            device_id = %s
            AND gps_time >= %s
            AND gps_time <= %s
        ORDER BY gps_time ASC, id ASC
        """
 
        cursor.execute(
            sql,
            (
                device_id,
                start_time,
                end_time,
            ),
        )
 
        rows = cursor.fetchall()
        return [row_to_location(row) for row in rows]
 
    except mysql.connector.Error as e:
        raise HTTPException(
            status_code=500,
            detail=f"轨迹查询失败: {str(e)}",
        )
 
    finally:
        if cursor:
            cursor.close()
 
        if conn and conn.is_connected():
            conn.close()
 
 
# ==================================================
# GET /locations/today
# 查询今天 00:00:00 到当前北京时间的轨迹
# ==================================================
 
@app.get("/locations/today")
def get_today_track(
    device_id: str = DEFAULT_DEVICE_ID,
):
    device_id = check_device_id(device_id)
 
    now = datetime.now(BEIJING_TZ).replace(
        tzinfo=None,
        microsecond=0,
    )
 
    today_start = datetime.combine(
        now.date(),
        time.min,
    )
 
    locations = query_track_range(
        device_id,
        today_start,
        now,
    )
 
    locations = simplify_track(locations)
 
    return {
        "device_id": device_id,
        "date": str(now.date()),
        "count": len(locations),
        "locations": locations,
    }
 
 
# ==================================================
# GET /locations/history/date
# 查询指定日期完整历史轨迹
# ==================================================
 
@app.get("/locations/history/date")
def get_history_by_date(
    date_str: str = Query(
        ...,
        description="日期，例如 2026-08-20",
    ),
    device_id: str = DEFAULT_DEVICE_ID,
):
    device_id = check_device_id(device_id)
 
    try:
        query_date = datetime.strptime(
            date_str,
            "%Y-%m-%d",
        ).date()
 
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="日期格式错误，应为 YYYY-MM-DD",
        )
 
    start_time = datetime.combine(
        query_date,
        time.min,
    )
 
    end_time = datetime.combine(
        query_date,
        time.max,
    )
 
    locations = query_track_range(
        device_id,
        start_time,
        end_time,
    )
 
    locations = simplify_track(locations)
 
    return {
        "device_id": device_id,
        "date": str(query_date),
        "count": len(locations),
        "locations": locations,
    }
 
 
# ==================================================
# GET /locations/history/range
# 自定义时间范围查询
#
# 示例：
# /locations/history/range
# ?start_time=2026-08-20T08:00:00
# &end_time=2026-08-20T12:00:00
# ==================================================
 
@app.get("/locations/history/range")
def get_history_range(
    start_time: datetime = Query(...),
    end_time: datetime = Query(...),
    device_id: str = DEFAULT_DEVICE_ID,
):
    device_id = check_device_id(device_id)
 
    start_time = normalize_query_datetime(start_time)
    end_time = normalize_query_datetime(end_time)
 
    if start_time >= end_time:
        raise HTTPException(
            status_code=400,
            detail="开始时间必须小于结束时间",
        )
 
    locations = query_track_range(
        device_id,
        start_time,
        end_time,
    )
 
    locations = simplify_track(locations)
 
    return {
        "device_id": device_id,
        "start_time": format_datetime(start_time),
        "end_time": format_datetime(end_time),
        "count": len(locations),
        "locations": locations,
    }
 
 
# ==================================================
# GET /locations/nearest
# 查询指定日期 + 时间前后 5 分钟内最接近的 GPS 点
# ==================================================
 
@app.get("/locations/nearest")
def get_nearest_location(
    date_str: str = Query(
        ...,
        description="日期 YYYY-MM-DD",
    ),
    time_str: str = Query(
        ...,
        description="时间 HH:MM:SS",
    ),
    device_id: str = DEFAULT_DEVICE_ID,
):
    device_id = check_device_id(device_id)
 
    try:
        target_datetime = datetime.strptime(
            f"{date_str} {time_str}",
            "%Y-%m-%d %H:%M:%S",
        )
 
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="时间格式错误，应为 YYYY-MM-DD + HH:MM:SS",
        )
 
    max_diff = timedelta(
        minutes=NEAREST_MAX_DIFF_MINUTES,
    )
 
    start_time = target_datetime - max_diff
    end_time = target_datetime + max_diff
 
    conn = None
    cursor = None
 
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
 
        sql = """
        SELECT
            id,
            device_id,
            longitude,
            latitude,
            gps_time,
            received_at
        FROM locations
        WHERE
            device_id = %s
            AND gps_time >= %s
            AND gps_time <= %s
        ORDER BY
            ABS(
                TIMESTAMPDIFF(
                    SECOND,
                    gps_time,
                    %s
                )
            ) ASC,
            id DESC
        LIMIT 1
        """
 
        cursor.execute(
            sql,
            (
                device_id,
                start_time,
                end_time,
                target_datetime,
            ),
        )
 
        row = cursor.fetchone()
 
        if row is None:
            return {
                "found": False,
                "device_id": device_id,
                "query_time": format_datetime(target_datetime),
                "message": (
                    f"该时间前后{NEAREST_MAX_DIFF_MINUTES}分钟暂无GPS数据"
                ),
            }
 
        gps_time = row[4]
        difference_seconds = abs(
            int(
                (gps_time - target_datetime).total_seconds()
            )
        )
 
        return {
            "found": True,
            "id": row[0],
            "device_id": row[1],
            "query_time": format_datetime(target_datetime),
            "gps_time": format_datetime(gps_time),
            "received_at": format_datetime(row[5]),
            "difference_seconds": difference_seconds,
            "longitude": float(row[2]),
            "latitude": float(row[3]),
        }
 
    except mysql.connector.Error as e:
        raise HTTPException(
            status_code=500,
            detail=f"指定时间位置查询失败: {str(e)}",
        )
 
    finally:
        if cursor:
            cursor.close()
 
        if conn and conn.is_connected():
            conn.close()
