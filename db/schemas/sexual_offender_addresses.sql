-- 성범죄자 거주지 테이블
CREATE TABLE IF NOT EXISTS sexual_offender_addresses (
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
CREATE INDEX IF NOT EXISTS idx_offender_district ON sexual_offender_addresses (district);
CREATE INDEX IF NOT EXISTS idx_offender_dong ON sexual_offender_addresses (dong);
CREATE INDEX IF NOT EXISTS idx_offender_location ON sexual_offender_addresses (latitude, longitude);