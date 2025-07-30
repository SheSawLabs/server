-- 가로등 테이블
CREATE TABLE IF NOT EXISTS street_lights (
    id SERIAL PRIMARY KEY,
    district VARCHAR(100),              -- 자치구
    dong VARCHAR(100),                  -- 동(행정동)
    address TEXT,                       -- 주소
    latitude DECIMAL(10, 7),            -- 위도
    longitude DECIMAL(11, 7),           -- 경도
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_streetlight_district ON street_lights (district);
CREATE INDEX IF NOT EXISTS idx_streetlight_dong ON street_lights (dong);
CREATE INDEX IF NOT EXISTS idx_streetlight_location ON street_lights (latitude, longitude);