 #include <TinyGPSPlus.h>
 #include <WiFi.h>
 #include <HTTPClient.h>
 #include <WebServer.h>
  
 // ============================================================
 // GPS
 //
 // 【重要】已经通过实际实验确认：
 //
 // 你的 GPS 小板上丝印“RX”的针脚会输出
 // $GPGGA / $GPRMC / $GPGSV 等 NMEA 数据。
 //
 // 所以在本项目中：
 // GPS板 RX -> ESP32 GPIO14
 //
 // 不再按照普通模块丝印方向进行推断。
 // 以后以这个实际测试结果为准。
 // ============================================================
  
 TinyGPSPlus gps;
 HardwareSerial GPSSerial(2);
  
 #define GPS_RX 14
 #define GPS_TX 13
  
 // ============================================================
 // 原来的 WiFi
 // ============================================================
  
 const char* WIFI_SSID = "YOUR_WIFI_SSID";
  
 // 请填写你自己的热点密码
 const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
  
 // ============================================================
 // FastAPI
 //
 // 把 YOUR_SERVER_IP 替换为运行 FastAPI 的电脑局域网 IPv4，
 // 例如：http://192.168.1.100:8000/location
 // 电脑 IP 改变时，只需修改这里。
 // ============================================================
  
 const char* SERVER_URL =
     "http://YOUR_SERVER_IP:8000/location";
  
 // ============================================================
 // 设备 ID
 // ============================================================
  
 const char* DEVICE_ID =
     "elder001";
  
 // ============================================================
 // 手机本地诊断热点
 //
 // 手机连接：
 // WiFi：GPS_MONITOR
 // 密码：12345678
 //
 // 浏览器：
 // http://192.168.4.1
 // ============================================================
  
 const char* DIAG_AP_SSID =
     "GPS_MONITOR";
  
 const char* DIAG_AP_PASSWORD =
     "12345678";
  
 WebServer diagServer(80);
  
 // ============================================================
 // 时间参数
 // ============================================================
  
 // 每 5 秒检查一次是否可以上传新的 GPS Fix
 const unsigned long UPLOAD_INTERVAL =
     5000;
  
 // 最新 GPS Fix 超过 10 秒认为过旧
 const unsigned long GPS_FIX_MAX_AGE_MS =
     10000;
  
 // WiFi 断开后每 10 秒重试
 const unsigned long WIFI_RECONNECT_INTERVAL =
     10000;
  
 // HTTP 超时
 const unsigned long HTTP_TIMEOUT_MS =
     2000;
  
 // GPS 超过 3 秒没有任何 UART 字符
 // 认为数据流可能已经断开
 const unsigned long GPS_UART_TIMEOUT_MS =
     3000;
  
 // ============================================================
 // 全局时间变量
 // ============================================================
  
 unsigned long lastUploadCheck = 0;
  
 unsigned long lastWiFiReconnectAttempt = 0;
  
 // 最近一次收到 GPS UART 字节的时间
 unsigned long lastGpsByteTime = 0;
  
 // ============================================================
 // GPS Fix
 // ============================================================
  
 struct GpsFix {
  
   bool valid = false;
  
   double latitude = 0.0;
   double longitude = 0.0;
  
   String gpsTimeUtc = "";
  
   uint64_t gpsTimeKey = 0;
  
   unsigned long capturedAt = 0;
 };
  
 GpsFix latestFix;
  
 // ============================================================
 // 最后一次成功上传记录
 // ============================================================
  
 uint64_t lastUploadedGpsTimeKey = 0;
  
 String lastUploadedGpsTime = "";
  
 // 最近 HTTP 状态码
 int lastHttpCode = 0;
  
 // 最近上传结果说明
 String lastUploadStatus =
     "尚未上传";
  
 // ============================================================
 // GPS 时间 Key
 // ============================================================
  
 uint64_t buildGpsTimeKey() {
  
   return
       (uint64_t)gps.date.year()   * 10000000000ULL +
       (uint64_t)gps.date.month()  *   100000000ULL +
       (uint64_t)gps.date.day()    *     1000000ULL +
       (uint64_t)gps.time.hour()   *       10000ULL +
       (uint64_t)gps.time.minute() *         100ULL +
       (uint64_t)gps.time.second();
 }
  
 // ============================================================
 // GPS UTC ISO8601
 // ============================================================
  
 String buildGpsUtcIso8601() {
  
   char buffer[25];
  
   snprintf(
       buffer,
       sizeof(buffer),
       "%04d-%02d-%02dT%02d:%02d:%02dZ",
       (int)gps.date.year(),
       (int)gps.date.month(),
       (int)gps.date.day(),
       (int)gps.time.hour(),
       (int)gps.time.minute(),
       (int)gps.time.second()
   );
  
   return String(buffer);
 }
  
 // ============================================================
 // 捕获新的有效 GPS Fix
 // ============================================================
  
 void captureLatestGpsFix() {
  
   if (!gps.location.isUpdated()) {
     return;
   }
  
   // 必须同时满足：
   // 位置有效
   // 日期有效
   // 时间有效
  
   if (
       !gps.location.isValid() ||
       !gps.date.isValid() ||
       !gps.time.isValid()
   ) {
  
     return;
   }
  
   latestFix.latitude =
       gps.location.lat();
  
   latestFix.longitude =
       gps.location.lng();
  
   latestFix.gpsTimeUtc =
       buildGpsUtcIso8601();
  
   latestFix.gpsTimeKey =
       buildGpsTimeKey();
  
   latestFix.capturedAt =
       millis();
  
   latestFix.valid =
       true;
  
   Serial.println();
   Serial.println(
       "========== 新 GPS Fix =========="
   );
  
   Serial.print(
       "卫星数: "
   );
  
   if (gps.satellites.isValid()) {
  
     Serial.println(
         gps.satellites.value()
     );
  
   } else {
  
     Serial.println(
         "未知"
     );
   }
  
   Serial.print(
       "纬度(WGS84): "
   );
  
   Serial.println(
       latestFix.latitude,
       6
   );
  
   Serial.print(
       "经度(WGS84): "
   );
  
   Serial.println(
       latestFix.longitude,
       6
   );
  
   Serial.print(
       "GPS UTC时间: "
   );
  
   Serial.println(
       latestFix.gpsTimeUtc
   );
  
   if (gps.hdop.isValid()) {
  
     Serial.print(
         "HDOP: "
     );
  
     Serial.println(
         gps.hdop.hdop(),
         2
     );
   }
  
   Serial.println(
       "================================"
   );
 }
  
 // ============================================================
 // 持续读取 GPS
 // ============================================================
  
 void readGPS() {
  
   while (
       GPSSerial.available()
   ) {
  
     char c =
         GPSSerial.read();
  
     // ------------------------------
     // 只要真正收到 UART 字节，
     // 就更新时间。
     //
     // 即使没有卫星定位，
     // 这里也应该持续变化。
     // ------------------------------
  
     lastGpsByteTime =
         millis();
  
     if (
         gps.encode(c)
     ) {
  
       captureLatestGpsFix();
     }
   }
 }
  
 // ============================================================
 // 判断 GPS UART 数据流是否正常
 // ============================================================
  
 bool isGpsUartAlive() {
  
   if (
       lastGpsByteTime == 0
   ) {
  
     return false;
   }
  
   return
       millis() - lastGpsByteTime
       < GPS_UART_TIMEOUT_MS;
 }
  
 // ============================================================
 // GPS 数据最后年龄
 // ============================================================
  
 unsigned long getGpsDataAge() {
  
   if (
       lastGpsByteTime == 0
   ) {
  
     return 999999999UL;
   }
  
   return
       millis() - lastGpsByteTime;
 }
  
 // ============================================================
 // WiFi 初始连接
 //
 // 注意：这里不再设置 WIFI_STA，
 // 因为我们需要同时使用：
 //
 // STA：连接 YOUR_WIFI_SSID
 // AP：给手机提供 GPS_MONITOR
 //
 // 所以 setup() 中使用 WIFI_AP_STA。
 // ============================================================
  
 void connectWiFi() {
  
   WiFi.begin(
       WIFI_SSID,
       WIFI_PASSWORD
   );
  
   Serial.print(
       "连接 WiFi"
   );
  
   unsigned long startTime =
       millis();
  
   unsigned long lastDot =
       0;
  
   while (
       WiFi.status() != WL_CONNECTED &&
       millis() - startTime < 15000
   ) {
  
     // 等 WiFi 时仍然读取 GPS
     readGPS();
  
     // 手机诊断网页也继续处理
     diagServer.handleClient();
  
     if (
         millis() - lastDot >= 500
     ) {
  
       lastDot =
           millis();
  
       Serial.print(".");
     }
  
     delay(10);
   }
  
   Serial.println();
  
   if (
       WiFi.status() == WL_CONNECTED
   ) {
  
     Serial.println(
         "WiFi 连接成功"
     );
  
     Serial.print(
         "ESP32 STA IP: "
     );
  
     Serial.println(
         WiFi.localIP()
     );
  
   } else {
  
     Serial.println(
         "WiFi 初始连接失败"
     );
  
     Serial.println(
         "不影响手机连接 GPS_MONITOR 查看 GPS 状态"
     );
   }
 }
  
 // ============================================================
 // WiFi 自动重连
 // ============================================================
  
 void maintainWiFi() {
  
   if (
       WiFi.status() == WL_CONNECTED
   ) {
  
     return;
   }
  
   if (
       millis() -
           lastWiFiReconnectAttempt
       <
       WIFI_RECONNECT_INTERVAL
   ) {
  
     return;
   }
  
   lastWiFiReconnectAttempt =
       millis();
  
   Serial.println(
       "WiFi 已断开，尝试重新连接..."
   );
  
   WiFi.begin(
       WIFI_SSID,
       WIFI_PASSWORD
   );
 }
  
 // ============================================================
 // 是否允许上传 GPS
 // ============================================================
  
 bool canUploadLatestFix() {
  
   if (
       !latestFix.valid
   ) {
  
     return false;
   }
  
   unsigned long fixAge =
       millis() -
       latestFix.capturedAt;
  
   if (
       fixAge >
       GPS_FIX_MAX_AGE_MS
   ) {
  
     return false;
   }
  
   if (
       latestFix.gpsTimeUtc.length()
       == 0
   ) {
  
     return false;
   }
  
   if (
       lastUploadedGpsTimeKey != 0 &&
       latestFix.gpsTimeKey <=
           lastUploadedGpsTimeKey
   ) {
  
     return false;
   }
  
   return true;
 }
  
 // ============================================================
 // 上传真实 GPS
 // ============================================================
  
 void uploadGPS() {
  
   if (
       WiFi.status() != WL_CONNECTED
   ) {
  
     lastUploadStatus =
         "WiFi未连接";
  
     return;
   }
  
   if (
       !canUploadLatestFix()
   ) {
  
     lastUploadStatus =
         "暂无新的有效GPS定位";
  
     return;
   }
  
   HTTPClient http;
  
   http.setTimeout(
       HTTP_TIMEOUT_MS
   );
  
   if (
       !http.begin(
           SERVER_URL
       )
   ) {
  
     lastUploadStatus =
         "HTTP初始化失败";
  
     return;
   }
  
   http.addHeader(
       "Content-Type",
       "application/json"
   );
  
   String body = "{";
  
   body +=
       "\"device_id\":\"";
  
   body +=
       DEVICE_ID;
  
   body +=
       "\"";
  
   body +=
       ",\"longitude\":";
  
   body +=
       String(
           latestFix.longitude,
           6
       );
  
   body +=
       ",\"latitude\":";
  
   body +=
       String(
           latestFix.latitude,
           6
       );
  
   body +=
       ",\"gps_time\":\"";
  
   body +=
       latestFix.gpsTimeUtc;
  
   body +=
       "\"";
  
   body +=
       "}";
  
   Serial.println();
  
   Serial.println(
       "========== HTTP POST =========="
   );
  
   Serial.println(body);
  
   int httpCode =
       http.POST(body);
  
   lastHttpCode =
       httpCode;
  
   Serial.print(
       "HTTP Code: "
   );
  
   Serial.println(
       httpCode
   );
  
   if (
       httpCode >= 200 &&
       httpCode < 300
   ) {
  
     lastUploadedGpsTimeKey =
         latestFix.gpsTimeKey;
  
     lastUploadedGpsTime =
         latestFix.gpsTimeUtc;
  
     lastUploadStatus =
         "上传成功";
  
     Serial.println(
         "GPS 上传成功"
     );
  
   } else if (
       httpCode > 0
   ) {
  
     lastUploadStatus =
         "服务器返回错误";
  
   } else {
  
     lastUploadStatus =
         "HTTP连接失败";
   }
  
   http.end();
 }
  
 // ============================================================
 // 手机诊断网页
 // ============================================================
  
 void handleDiagnosticPage() {
  
   unsigned long gpsAge =
       getGpsDataAge();
  
   bool uartAlive =
       isGpsUartAlive();
  
   bool locationValid =
       gps.location.isValid();
  
   // ----------------------------------------------------------
   // 页面开始
   // ----------------------------------------------------------
  
   String html;
  
   html.reserve(7000);
  
   html +=
       "<!DOCTYPE html>";
  
   html +=
       "<html>";
  
   html +=
       "<head>";
  
   html +=
       "<meta charset='UTF-8'>";
  
   // 每 2 秒自动刷新
   html +=
       "<meta http-equiv='refresh' content='2'>";
  
   html +=
       "<meta name='viewport' "
       "content='width=device-width,"
       "initial-scale=1'>";
  
   html +=
       "<title>ESP32 GPS Monitor</title>";
  
   // ----------------------------------------------------------
   // CSS
   // ----------------------------------------------------------
  
   html +=
       "<style>";
  
   html +=
       "body{"
       "font-family:Arial,sans-serif;"
       "margin:0;"
       "padding:16px;"
       "background:#f2f3f5;"
       "color:#222;"
       "}";
  
   html +=
       ".title{"
       "font-size:24px;"
       "font-weight:bold;"
       "margin-bottom:15px;"
       "}";
  
   html +=
       ".box{"
       "background:white;"
       "padding:16px;"
       "margin-bottom:12px;"
       "border-radius:12px;"
       "box-shadow:0 1px 5px "
       "rgba(0,0,0,0.08);"
       "}";
  
   html +=
       ".ok{"
       "color:#16803c;"
       "font-weight:bold;"
       "font-size:20px;"
       "}";
  
   html +=
       ".bad{"
       "color:#c62828;"
       "font-weight:bold;"
       "font-size:20px;"
       "}";
  
   html +=
       ".warn{"
       "color:#d07a00;"
       "font-weight:bold;"
       "font-size:20px;"
       "}";
  
   html +=
       "table{"
       "width:100%;"
       "border-collapse:collapse;"
       "}";
  
   html +=
       "td{"
       "padding:8px 4px;"
       "border-bottom:1px solid #eee;"
       "}";
  
   html +=
       "td:first-child{"
       "color:#666;"
       "width:50%;"
       "}";
  
   html +=
       "</style>";
  
   html +=
       "</head>";
  
   html +=
       "<body>";
  
   html +=
       "<div class='title'>"
       "ESP32 + L80-R GPS 实时监测"
       "</div>";
  
   // ==========================================================
   // 第一块：总体状态
   // ==========================================================
  
   html +=
       "<div class='box'>";
  
   html +=
       "<h3>总体状态</h3>";
  
   if (
       locationValid &&
       latestFix.valid
   ) {
  
     html +=
         "<div class='ok'>"
         "● GPS 已定位"
         "</div>";
  
   } else if (
       uartAlive
   ) {
  
     html +=
         "<div class='warn'>"
         "● GPS 正在工作，等待定位"
         "</div>";
  
   } else {
  
     html +=
         "<div class='bad'>"
         "● GPS UART 数据流异常"
         "</div>";
   }
  
   html +=
       "</div>";
  
   // ==========================================================
   // 第二块：GPS UART
   // ==========================================================
  
   html +=
       "<div class='box'>";
  
   html +=
       "<h3>GPS UART 数据流</h3>";
  
   if (
       uartAlive
   ) {
  
     html +=
         "<p class='ok'>"
         "UART 正常"
         "</p>";
  
   } else {
  
     html +=
         "<p class='bad'>"
         "UART 无数据 / 数据流可能已断"
         "</p>";
   }
  
   html +=
       "<table>";
  
   html +=
       "<tr><td>GPS累计字符</td><td>";
  
   html +=
       String(
           gps.charsProcessed()
       );
  
   html +=
       "</td></tr>";
  
   html +=
       "<tr><td>有效NMEA语句</td><td>";
  
   html +=
       String(
           gps.passedChecksum()
       );
  
   html +=
       "</td></tr>";
  
   html +=
       "<tr><td>校验失败</td><td>";
  
   html +=
       String(
           gps.failedChecksum()
       );
  
   html +=
       "</td></tr>";
  
   html +=
       "<tr><td>距最后GPS字符</td><td>";
  
   if (
       lastGpsByteTime == 0
   ) {
  
     html +=
         "从未收到";
  
   } else {
  
     html +=
         String(gpsAge);
  
     html +=
         " ms";
   }
  
   html +=
       "</td></tr>";
  
   html +=
       "</table>";
  
   html +=
       "</div>";
  
   // ==========================================================
   // 第三块：定位状态
   // ==========================================================
  
   html +=
       "<div class='box'>";
  
   html +=
       "<h3>GPS 定位状态</h3>";
  
   if (
       locationValid
   ) {
  
     html +=
         "<p class='ok'>"
         "定位有效"
         "</p>";
  
   } else {
  
     html +=
         "<p class='warn'>"
         "暂无有效定位"
         "</p>";
   }
  
   html +=
       "<table>";
  
   // --------------------------
   // 卫星
   // --------------------------
  
   html +=
       "<tr><td>卫星数</td><td>";
  
   if (
       gps.satellites.isValid()
   ) {
  
     html +=
         String(
             gps.satellites.value()
         );
  
   } else {
  
     html +=
         "未知";
   }
  
   html +=
       "</td></tr>";
  
   // --------------------------
   // HDOP
   // --------------------------
  
   html +=
       "<tr><td>HDOP</td><td>";
  
   if (
       gps.hdop.isValid()
   ) {
  
     html +=
         String(
             gps.hdop.hdop(),
             2
         );
  
   } else {
  
     html +=
         "未知";
   }
  
   html +=
       "</td></tr>";
  
   // --------------------------
   // 纬度
   // --------------------------
  
   html +=
       "<tr><td>纬度</td><td>";
  
   if (
       gps.location.isValid()
   ) {
  
     html +=
         String(
             gps.location.lat(),
             6
         );
  
   } else {
  
     html +=
         "--";
   }
  
   html +=
       "</td></tr>";
  
   // --------------------------
   // 经度
   // --------------------------
  
   html +=
       "<tr><td>经度</td><td>";
  
   if (
       gps.location.isValid()
   ) {
  
     html +=
         String(
             gps.location.lng(),
             6
         );
  
   } else {
  
     html +=
         "--";
   }
  
   html +=
       "</td></tr>";
  
   // --------------------------
   // GPS时间
   // --------------------------
  
   html +=
       "<tr><td>GPS UTC时间</td><td>";
  
   if (
       latestFix.valid
   ) {
  
     html +=
         latestFix.gpsTimeUtc;
  
   } else {
  
     html +=
         "--";
   }
  
   html +=
       "</td></tr>";
  
   // --------------------------
   // 最近 Fix 年龄
   // --------------------------
  
   html +=
       "<tr><td>最近有效定位距今</td><td>";
  
   if (
       latestFix.valid
   ) {
  
     html +=
         String(
             millis() -
             latestFix.capturedAt
         );
  
     html +=
         " ms";
  
   } else {
  
     html +=
         "尚未定位";
   }
  
   html +=
       "</td></tr>";
  
   html +=
       "</table>";
  
   html +=
       "</div>";
  
   // ==========================================================
   // 第四块：ESP32
   // ==========================================================
  
   html +=
       "<div class='box'>";
  
   html +=
       "<h3>ESP32 状态</h3>";
  
   html +=
       "<table>";
  
   html +=
       "<tr><td>运行时间</td><td>";
  
   html +=
       String(
           millis() / 1000
       );
  
   html +=
       " 秒</td></tr>";
  
   html +=
       "<tr><td>原 WiFi</td><td>";
  
   if (
       WiFi.status() ==
       WL_CONNECTED
   ) {
  
     html +=
         "已连接";
  
   } else {
  
     html +=
         "未连接";
   }
  
   html +=
       "</td></tr>";
  
   html +=
       "<tr><td>WiFi RSSI</td><td>";
  
   if (
       WiFi.status() ==
       WL_CONNECTED
   ) {
  
     html +=
         String(
             WiFi.RSSI()
         );
  
     html +=
         " dBm";
  
   } else {
  
     html +=
         "--";
   }
  
   html +=
       "</td></tr>";
  
   html +=
       "<tr><td>诊断热点</td><td>";
  
   html +=
       DIAG_AP_SSID;
  
   html +=
       "</td></tr>";
  
   html +=
       "<tr><td>诊断 IP</td><td>";
  
   html +=
       WiFi.softAPIP().toString();
  
   html +=
       "</td></tr>";
  
   html +=
       "</table>";
  
   html +=
       "</div>";
  
   // ==========================================================
   // 第五块：服务器上传
   // ==========================================================
  
   html +=
       "<div class='box'>";
  
   html +=
       "<h3>FastAPI 上传状态</h3>";
  
   html +=
       "<table>";
  
   html +=
       "<tr><td>最近上传状态</td><td>";
  
   html +=
       lastUploadStatus;
  
   html +=
       "</td></tr>";
  
   html +=
       "<tr><td>最近 HTTP Code</td><td>";
  
   html +=
       String(
           lastHttpCode
       );
  
   html +=
       "</td></tr>";
  
   html +=
       "<tr><td>最后成功GPS时间</td><td>";
  
   if (
       lastUploadedGpsTime.length()
       > 0
   ) {
  
     html +=
         lastUploadedGpsTime;
  
   } else {
  
     html +=
         "--";
   }
  
   html +=
       "</td></tr>";
  
   html +=
       "</table>";
  
   html +=
       "</div>";
  
   // ==========================================================
   // 使用说明
   // ==========================================================
  
   html +=
       "<div class='box'>";
  
   html +=
       "<b>判断方法：</b><br><br>";
  
   html +=
       "1. GPS累计字符不断增加："
       "GPS与ESP32串口正常。<br><br>";
  
   html +=
       "2. UART正常但卫星数为0："
       "模块在工作，只是暂时没有搜到卫星。<br><br>";
  
   html +=
       "3. 显示GPS已定位："
       "下面会直接出现真实经纬度。<br><br>";
  
   html +=
       "4. GPS累计字符停止增长，"
       "同时距最后字符越来越大："
       "重点检查杜邦线、VCC、GND、GPIO14。<br><br>";
  
   html +=
       "5. ESP32运行时间突然重新变小："
       "说明ESP32可能发生了重启。";
  
   html +=
       "</div>";
  
   html +=
       "<p style='text-align:center;color:#777;'>"
       "页面每2秒自动刷新"
       "</p>";
  
   html +=
       "</body>";
  
   html +=
       "</html>";
  
   diagServer.send(
       200,
       "text/html; charset=utf-8",
       html
   );
 }
  
 // ============================================================
 // 启动手机诊断热点
 // ============================================================
  
 void startDiagnosticServer() {
  
   bool apResult =
       WiFi.softAP(
           DIAG_AP_SSID,
           DIAG_AP_PASSWORD
       );
  
   if (
       apResult
   ) {
  
     Serial.println(
         "诊断热点启动成功"
     );
  
     Serial.print(
         "WiFi名称: "
     );
  
     Serial.println(
         DIAG_AP_SSID
     );
  
     Serial.print(
         "诊断网址: http://"
     );
  
     Serial.println(
         WiFi.softAPIP()
     );
  
   } else {
  
     Serial.println(
         "诊断热点启动失败"
     );
   }
  
   diagServer.on(
       "/",
       HTTP_GET,
       handleDiagnosticPage
   );
  
   diagServer.begin();
  
   Serial.println(
       "诊断网页服务器启动完成"
   );
 }
  
 // ============================================================
 // setup
 // ============================================================
  
 void setup() {
  
   Serial.begin(
       115200
   );
  
   delay(1000);
  
   Serial.println();
   Serial.println(
       "================================"
   );
  
   Serial.println(
       "L80-R + ESP32 GPS系统"
   );
  
   Serial.println(
       "GPS + WiFi + FastAPI + 手机诊断"
   );
  
   Serial.println(
       "================================"
   );
  
   // ----------------------------------------------------------
   // GPS UART
   // ----------------------------------------------------------
  
   GPSSerial.begin(
       9600,
       SERIAL_8N1,
       GPS_RX,
       GPS_TX
   );
  
   Serial.println(
       "GPS UART 初始化完成"
   );
  
   Serial.println(
       "GPS板 RX -> ESP32 GPIO14"
   );
  
   // ----------------------------------------------------------
   // 同时启用：
   // AP = 手机诊断
   // STA = 原来的 YOUR_WIFI_SSID
   // ----------------------------------------------------------
  
   WiFi.mode(
       WIFI_AP_STA
   );
  
   // ----------------------------------------------------------
   // 首先建立手机诊断热点
   // 即使 YOUR_WIFI_SSID 连不上，手机仍然可以看状态。
   // ----------------------------------------------------------
  
   startDiagnosticServer();
  
   // ----------------------------------------------------------
   // 再连接原来的 WiFi
   // ----------------------------------------------------------
  
   connectWiFi();
  
   Serial.println();
  
   Serial.println(
       "系统初始化完成"
   );
  
   Serial.println(
       "手机请连接：GPS_MONITOR"
   );
  
   Serial.println(
       "密码：12345678"
   );
  
   Serial.println(
       "浏览器打开：http://192.168.4.1"
   );
 }
  
 // ============================================================
 // loop
 // ============================================================
  
 void loop() {
  
   // ----------------------------------------------------------
   // 1. GPS必须最高频率持续读取
   // ----------------------------------------------------------
  
   readGPS();
  
   // ----------------------------------------------------------
   // 2. 手机网页
   // ----------------------------------------------------------
  
   diagServer.handleClient();
  
   // ----------------------------------------------------------
   // 3. 维护原来的 WiFi
   // ----------------------------------------------------------
  
   maintainWiFi();
  
   // ----------------------------------------------------------
   // 4. 每5秒尝试上传一次新的有效定位
   // ----------------------------------------------------------
  
   if (
       millis() -
           lastUploadCheck
       >=
       UPLOAD_INTERVAL
   ) {
  
     lastUploadCheck =
         millis();
  
     uploadGPS();
   }
  
   // 不要在这里加长时间 delay()
 }
