-- 치안안전시설 테이블
CREATE TABLE IF NOT EXISTS crime_safety_facilities (
    id SERIAL PRIMARY KEY,
    district VARCHAR(100),              -- 자치구
    dong VARCHAR(100),                  -- 동(행정동)
    address TEXT,                       -- 주소
    latitude DECIMAL(10, 7),            -- 위도
    longitude DECIMAL(11, 7),           -- 경도
    facility_type VARCHAR(100),         -- 시설 유형
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_crime_safety_district ON crime_safety_facilities (district);
CREATE INDEX IF NOT EXISTS idx_crime_safety_dong ON crime_safety_facilities (dong);
CREATE INDEX IF NOT EXISTS idx_crime_safety_location ON crime_safety_facilities (latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_crime_safety_type ON crime_safety_facilities (facility_type);