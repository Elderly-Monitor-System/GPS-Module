from datetime import datetime, time, timedelta

from fastapi import FastAPI, HTTPException, Query

from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel

import mysql.connector

import math

import os

from dotenv import load_dotenv


# ==================================================
# 环境变量
# ==================================================

load_dotenv()


# ==================================================
# 创建FastAPI应用
# ==================================================

app = FastAPI(

    title="老人GPS定位监护系统",

    description="老人实时定位、今日轨迹、历史轨迹查询",

    version="1.0"

)



# ==================================================
# CORS跨域配置
# ==================================================

app.add_middleware(

    CORSMiddleware,

    allow_origins=[

        "http://127.0.0.1:5500",

        "http://localhost:5500"

    ],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"]

)



# ==================================================
# 默认设备
# ==================================================

DEFAULT_DEVICE_ID = "elder001"



# ==================================================
# MySQL数据库连接
# ==================================================

def get_db_connection():

    return mysql.connector.connect(

        host=os.getenv(

            "MYSQL_HOST",

            "127.0.0.1"

        ),

        port=int(os.getenv(

            "MYSQL_PORT",

            3306

        )),

        user=os.getenv(

            "MYSQL_USER",

            "root"

        ),

        password=os.getenv(

            "MYSQL_PASSWORD"

        ),

        database=os.getenv(

            "MYSQL_DATABASE",

            "elder_monitor"

        ),

        charset="utf8mb4"

    )



# ==================================================
# GPS上传数据模型
# ==================================================

class LocationData(BaseModel):

    device_id: str

    longitude: float

    latitude: float



# ==================================================
# 坐标合法性检查
# ==================================================

def check_coordinate(

    longitude,

    latitude

):

    if not (-180 <= longitude <= 180):

        raise HTTPException(

            status_code=400,

            detail="经度范围错误"

        )


    if not (-90 <= latitude <= 90):

        raise HTTPException(

            status_code=400,

            detail="纬度范围错误"

        )



# ==================================================
# GET /location
#
# 获取最新GPS位置
# ==================================================

@app.get("/location")

def get_location():

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

            timestamp

        FROM locations

        ORDER BY id DESC

        LIMIT 1

        """


        cursor.execute(sql)


        row = cursor.fetchone()


        if row is None:

            return {

                "message":

                "暂无GPS数据"

            }


        return {


            "id":

            row[0],


            "device_id":

            row[1],


            "longitude":

            row[2],


            "latitude":

            row[3],


            "timestamp":

            str(row[4])


        }



    except mysql.connector.Error as e:


        raise HTTPException(

            status_code=500,

            detail=f"数据库读取失败:{str(e)}"

        )


    finally:


        if cursor:

            cursor.close()


        if conn and conn.is_connected():

            conn.close()




# ==================================================
# POST /location
#
# 上传GPS数据
# ==================================================

@app.post("/location")

def upload_location(

    data: LocationData

):

    conn = None

    cursor = None


    try:


        if not data.device_id.strip():

            raise HTTPException(

                status_code=400,

                detail="device_id不能为空"

            )



        check_coordinate(

            data.longitude,

            data.latitude

        )



        conn = get_db_connection()


        cursor = conn.cursor()



        sql = """

        INSERT INTO locations

        (

            device_id,

            longitude,

            latitude

        )

        VALUES

        (

            %s,

            %s,

            %s

        )

        """



        cursor.execute(

            sql,

            (

                data.device_id.strip(),

                data.longitude,

                data.latitude

            )

        )


        conn.commit()



        return {


            "message":

            "GPS上传成功",


            "id":

            cursor.lastrowid,


            "device_id":

            data.device_id,


            "longitude":

            data.longitude,


            "latitude":

            data.latitude


        }



    except mysql.connector.Error as e:


        raise HTTPException(

            status_code=500,

            detail=f"数据库写入失败:{str(e)}"

        )


    finally:


        if cursor:

            cursor.close()


        if conn and conn.is_connected():

            conn.close()




# ==================================================
# GPS距离计算
# ==================================================

def calculate_distance(

    lon1,

    lat1,

    lon2,

    lat2

):

    EARTH_RADIUS = 6371000



    rad_lat1 = math.radians(lat1)

    rad_lat2 = math.radians(lat2)



    delta_lat = math.radians(

        lat2-lat1

    )


    delta_lon = math.radians(

        lon2-lon1

    )



    a = (

        math.sin(delta_lat/2)**2

        +

        math.cos(rad_lat1)

        *

        math.cos(rad_lat2)

        *

        math.sin(delta_lon/2)**2

    )


    c = 2 * math.atan2(

        math.sqrt(a),

        math.sqrt(1-a)

    )


    return EARTH_RADIUS*c




# ==================================================
# 轨迹抽稀
# ==================================================

def simplify_track(

    locations,

    distance_threshold=50

):


    if len(locations)<=2:

        return locations



    result=[]


    result.append(

        locations[0]

    )


    last_point=locations[0]



    for point in locations[1:]:


        distance = calculate_distance(

            last_point["longitude"],

            last_point["latitude"],

            point["longitude"],

            point["latitude"]

        )


        if distance >= distance_threshold:


            result.append(point)

            last_point=point



    if result[-1]["id"] != locations[-1]["id"]:

        result.append(

            locations[-1]

        )


    return result



# ==================================================
# 查询轨迹公共函数
# ==================================================

def query_track_range(

    device_id,

    start_time,

    end_time

):

    conn=None

    cursor=None


    try:


        conn=get_db_connection()


        cursor=conn.cursor()



        sql="""


        SELECT

            id,

            device_id,

            longitude,

            latitude,

            timestamp


        FROM locations


        WHERE


            device_id=%s

            AND timestamp >= %s

            AND timestamp <= %s


        ORDER BY


            timestamp ASC,

            id ASC


        """



        cursor.execute(

            sql,

            (

                device_id,

                start_time,

                end_time

            )

        )



        rows=cursor.fetchall()


        locations=[]


        for row in rows:


            locations.append(

                {


                    "id":row[0],


                    "device_id":row[1],


                    "longitude":float(row[2]),


                    "latitude":float(row[3]),


                    "timestamp":str(row[4])


                }

            )



        return locations



    finally:


        if cursor:

            cursor.close()


        if conn and conn.is_connected():

            conn.close()
          # ==================================================
# GET /locations/today
#
# 查询今日轨迹
# ==================================================

@app.get("/locations/today")

def get_today_track(

    device_id: str = DEFAULT_DEVICE_ID

):

    now = datetime.now()


    today_start = datetime.combine(

        now.date(),

        time.min

    )


    locations = query_track_range(

        device_id,

        today_start,

        now

    )


    locations = simplify_track(

        locations,

        50

    )


    return {


        "device_id":

        device_id,


        "date":

        str(now.date()),


        "count":

        len(locations),


        "locations":

        locations


    }




# ==================================================
# GET /locations/history/date
#
# 查询指定日期历史轨迹
# ==================================================

@app.get("/locations/history/date")

def get_history_by_date(

    date_str: str = Query(

        ...,

        description="日期 YYYY-MM-DD"

    ),

    device_id: str = DEFAULT_DEVICE_ID

):


    try:


        query_date = datetime.strptime(

            date_str,

            "%Y-%m-%d"

        ).date()



    except ValueError:


        raise HTTPException(

            status_code=400,

            detail="日期格式错误，应为YYYY-MM-DD"

        )



    start_time = datetime.combine(

        query_date,

        time.min

    )


    end_time = datetime.combine(

        query_date,

        time.max

    )



    locations = query_track_range(

        device_id,

        start_time,

        end_time

    )



    locations = simplify_track(

        locations,

        50

    )



    return {


        "device_id":

        device_id,


        "date":

        str(query_date),


        "count":

        len(locations),


        "locations":

        locations


    }





# ==================================================
# GET /locations/history/range
#
# 自定义时间范围查询
# ==================================================

@app.get("/locations/history/range")

def get_history_range(

    start_time: datetime = Query(...),

    end_time: datetime = Query(...),

    device_id: str = DEFAULT_DEVICE_ID

):


    if start_time >= end_time:


        raise HTTPException(

            status_code=400,

            detail="开始时间必须小于结束时间"

        )



    locations = query_track_range(

        device_id,

        start_time,

        end_time

    )



    locations = simplify_track(

        locations,

        50

    )



    return {


        "device_id":

        device_id,


        "start_time":

        str(start_time),


        "end_time":

        str(end_time),


        "count":

        len(locations),


        "locations":

        locations


    }





# ==================================================
# GET /locations/nearest
#
# 查询指定时间附近最近GPS点
# ==================================================

@app.get("/locations/nearest")

def get_nearest_location(

    date_str: str = Query(

        ...,

        description="日期 YYYY-MM-DD"

    ),


    time_str: str = Query(

        ...,

        description="时间 HH:MM:SS"

    ),


    device_id: str = DEFAULT_DEVICE_ID

):


    try:


        target_datetime = datetime.strptime(

            f"{date_str} {time_str}",

            "%Y-%m-%d %H:%M:%S"

        )


    except ValueError:


        raise HTTPException(

            status_code=400,

            detail="时间格式错误"

        )



    max_diff = timedelta(

        minutes=5

    )


    start_time = (

        target_datetime

        -

        max_diff

    )


    end_time = (

        target_datetime

        +

        max_diff

    )



    conn=None

    cursor=None



    try:


        conn=get_db_connection()


        cursor=conn.cursor()



        sql="""


        SELECT


            id,

            device_id,

            longitude,

            latitude,

            timestamp



        FROM locations



        WHERE


            device_id=%s


            AND timestamp >= %s


            AND timestamp <= %s



        ORDER BY


            ABS(

                TIMESTAMPDIFF(

                    SECOND,

                    timestamp,

                    %s

                )

            )



        LIMIT 1


        """



        cursor.execute(

            sql,

            (

                device_id,

                start_time,

                end_time,

                target_datetime

            )

        )



        row=cursor.fetchone()



        if row is None:


            return {


                "found":

                False,


                "message":

                "该时间附近暂无GPS数据"


            }



        gps_time=row[4]



        diff_seconds=abs(

            int(

                (

                    gps_time

                    -

                    target_datetime

                ).total_seconds()

            )

        )



        return {


            "found":

            True,


            "query_time":

            target_datetime.strftime(

                "%Y-%m-%d %H:%M:%S"

            ),


            "gps_time":

            str(gps_time),


            "difference_seconds":

            diff_seconds,


            "longitude":

            float(row[2]),


            "latitude":

            float(row[3]),


            "id":

            row[0]


        }



    finally:


        if cursor:

            cursor.close()


        if conn and conn.is_connected():

            conn.close()





# ==================================================
# 根路径测试
# ==================================================

@app.get("/")

def root():


    return {


        "message":

        "老人GPS定位监护系统运行正常"


    }
