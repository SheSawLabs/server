-- 안심택배함 테이블
CREATE TABLE IF NOT EXISTS safe_delivery_boxes (
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
CREATE INDEX IF NOT EXISTS idx_delivery_district ON safe_delivery_boxes (district);
CREATE INDEX IF NOT EXISTS idx_delivery_dong ON safe_delivery_boxes (dong);
CREATE INDEX IF NOT EXISTS idx_delivery_location ON safe_delivery_boxes (latitude, longitude);