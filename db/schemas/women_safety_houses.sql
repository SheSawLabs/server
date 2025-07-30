-- 여성안심지킴이집 테이블
CREATE TABLE IF NOT EXISTS women_safety_houses (
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
CREATE INDEX IF NOT EXISTS idx_women_safety_district ON women_safety_houses (district);
CREATE INDEX IF NOT EXISTS idx_women_safety_dong ON women_safety_houses (dong);
CREATE INDEX IF NOT EXISTS idx_women_safety_location ON women_safety_houses (latitude, longitude);