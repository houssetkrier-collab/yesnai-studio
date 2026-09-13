-- 每账号独立签到时刻表：NULL = 跟随 autocheckin_config 全局时刻表
ALTER TABLE accounts ADD COLUMN weekday_times TEXT;
ALTER TABLE accounts ADD COLUMN weekend_times TEXT;
