-- 공통 함수 및 트리거 정의

-- 업데이트 시간 자동 갱신 함수
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 각 테이블에 업데이트 트리거 생성
CREATE TRIGGER IF NOT EXISTS update_cctv_updated_at
    BEFORE UPDATE ON cctv_installations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER IF NOT EXISTS update_delivery_updated_at
    BEFORE UPDATE ON safe_delivery_boxes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER IF NOT EXISTS update_streetlight_updated_at
    BEFORE UPDATE ON street_lights
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER IF NOT EXISTS update_offender_updated_at
    BEFORE UPDATE ON sexual_offender_addresses
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER IF NOT EXISTS update_women_safety_updated_at
    BEFORE UPDATE ON women_safety_houses
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER IF NOT EXISTS update_crime_safety_updated_at
    BEFORE UPDATE ON crime_safety_facilities
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();