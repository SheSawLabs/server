-- 가로등 테이블
CREATE TABLE IF NOT EXISTS streetlight_installations (
    id SERIAL PRIMARY KEY,
    management_number VARCHAR(100),     -- 관리번호
    district VARCHAR(100),              -- 자치구
    dong VARCHAR(100),                  -- 동(행정동)
    latitude DECIMAL(10, 7),            -- 위도
    longitude DECIMAL(11, 7),           -- 경도
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_streetlight_district ON streetlight_installations (district);
CREATE INDEX IF NOT EXISTS idx_streetlight_dong ON streetlight_installations (dong);
CREATE INDEX IF NOT EXISTS idx_streetlight_management ON streetlight_installations (management_number);
CREATE INDEX IF NOT EXISTS idx_streetlight_location ON streetlight_installations (latitude, longitude);