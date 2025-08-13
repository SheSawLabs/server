-- 알림 키워드 테이블 생성
CREATE TABLE IF NOT EXISTS notification_keywords (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  keyword VARCHAR(100) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(user_id, keyword)  -- 사용자별 키워드 중복 방지
);

-- 인덱스 생성 (검색 성능 향상)
CREATE INDEX IF NOT EXISTS idx_notification_keywords_user_id ON notification_keywords(user_id);
CREATE INDEX IF NOT EXISTS idx_notification_keywords_keyword ON notification_keywords(keyword);
