-- ============================================================
-- 老人GPS定位监护系统 · 数据库初始化脚本
-- MySQL 8.0 · 数据库名：elder_monitor
-- ============================================================
-- 适用于 v2.0.0 全新安装。
-- 从 v0.1.0 升级的旧库，请使用下方“旧库迁移”部分。
-- ============================================================

CREATE DATABASE IF NOT EXISTS elder_monitor
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE elder_monitor;

-- ------------------------------------------------------------
-- locations 定位记录表
-- ------------------------------------------------------------
-- gps_time     GPS 实际定位时间。ESP32 上传 UTC，后端统一转为
--              北京时间（UTC+8）的无时区 DATETIME 后写入。
-- received_at  服务器收到并写入数据的时间，由 MySQL 自动生成，
--              用于分析网络延迟、离线补传等，不参与业务展示。
-- longitude / latitude
--              保存 GPS 原始 WGS84 坐标，不在数据库中做坐标系
--              转换；高德地图 GCJ-02 转换只在前端展示层完成。
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS locations (
    id          BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键',
    device_id   VARCHAR(64)  NOT NULL COMMENT '设备标识，默认 elder001，预留多设备',
    longitude   DOUBLE       NOT NULL COMMENT '经度（WGS84）',
    latitude    DOUBLE       NOT NULL COMMENT '纬度（WGS84）',
    gps_time    DATETIME     NOT NULL COMMENT 'GPS实际定位时间（北京时间）',
    received_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '服务器接收写入时间',
    PRIMARY KEY (id),
    INDEX idx_locations_device_gps_time (device_id, gps_time)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COMMENT = '老人GPS定位记录表';

-- ============================================================
-- 旧库迁移（v0.1.0 → v2.0.0）
-- ============================================================
-- v0.1.0 的表只有 id / device_id / longitude / latitude / timestamp，
-- 其中 timestamp 是 MySQL 写入时间，没有真实 GPS 定位时间。
--
-- 迁移步骤（执行前请先备份数据库）：
--
--   1. 把旧 timestamp 改名并作为 received_at 保留：
--      ALTER TABLE locations
--          CHANGE COLUMN timestamp received_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
--          ADD COLUMN gps_time DATETIME NULL AFTER latitude;
--
--   2. 旧数据没有真实 GPS 时间，先用接收时间补齐作为历史兼容值：
--      UPDATE locations SET gps_time = received_at WHERE gps_time IS NULL;
--
--   3. 新后端要求 gps_time 必须有值：
--      ALTER TABLE locations MODIFY COLUMN gps_time DATETIME NOT NULL;
--
--   4. 建立联合索引（device_id + gps_time）：
--      CREATE INDEX idx_locations_device_gps_time
--          ON locations (device_id, gps_time);
--
-- 注意：如果 SHOW CREATE TABLE locations; 显示的表结构与上述不一致，
-- 不要机械执行，先按实际表结构调整。
-- 从 ESP32 开始上传 gps_time 之后的新数据才是真正的 GPS 定位时间。
-- ============================================================
