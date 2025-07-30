-- CCTV 설치 현황 테이블
CREATE TABLE IF NOT EXISTS cctv_installations (
    id SERIAL PRIMARY KEY,
    district VARCHAR(100),              -- 자치구
    dong VARCHAR(100),                  -- 동(행정동)
    address TEXT,                       -- 주소
    latitude DECIMAL(10, 7),            -- 위도 (WGSXPT)
    longitude DECIMAL(11, 7),           -- 경도 (WGSYPT)
    cctv_count INTEGER DEFAULT 1,       -- CCTV 개수
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_cctv_district ON cctv_installations (district);
CREATE INDEX IF NOT EXISTS idx_cctv_dong ON cctv_installations (dong);
CREATE INDEX IF NOT EXISTS idx_cctv_location ON cctv_installations (latitude, longitude);