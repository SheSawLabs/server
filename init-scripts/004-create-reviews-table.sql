-- 리뷰 테이블 생성
CREATE TABLE IF NOT EXISTS reviews (
  id VARCHAR(36) PRIMARY KEY,
  user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
  review_text TEXT,
  location VARCHAR(255),
  time_of_day VARCHAR(50),
  rating INTEGER CHECK (rating >= 1 AND rating <= 5),
  selected_keywords JSONB NOT NULL DEFAULT '[]',
  recommended_keywords JSONB DEFAULT '[]',
  score_result JSONB DEFAULT '{}',
  context_analysis JSONB DEFAULT '{}',
  analysis_method VARCHAR(20) NOT NULL CHECK (analysis_method IN ('gpt', 'restricted', 'keywords_only')),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_reviews_created_at ON reviews(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_reviews_location ON reviews(location);
CREATE INDEX IF NOT EXISTS idx_reviews_user_id ON reviews(user_id);
CREATE INDEX IF NOT EXISTS idx_reviews_analysis_method ON reviews(analysis_method);
CREATE INDEX IF NOT EXISTS idx_reviews_safety_level ON reviews ((score_result->>'safetyLevel'));
CREATE INDEX IF NOT EXISTS idx_reviews_selected_keywords ON reviews USING GIN (selected_keywords);

-- 샘플 데이터 삽입
INSERT INTO reviews (
  id, review_text, location, time_of_day, rating, 
  selected_keywords, score_result, analysis_method
) VALUES 
(
  gen_random_uuid()::text,
  '밤에 이 길을 걸으면 가로등이 부족해서 너무 어둡고 무서워요',
  '강남구 역삼동',
  '밤',
  2,
  '[{"category": "자연적 감시", "keyword": "어두움"}, {"category": "감정형", "keyword": "불안"}]'::jsonb,
  '{"totalScore": -25, "safetyLevel": "위험", "categoryScores": {"naturalSurveillance": -30, "emotional": -15}}'::jsonb,
  'restricted'
),
(
  gen_random_uuid()::text,
  '공원 근처라서 사람들이 많이 다니고 밝아서 안전해 보여요',
  '서초구 서초동',
  '오후',
  4,
  '[{"category": "자연적 감시", "keyword": "밝음"}, {"category": "활동 활성화", "keyword": "공원있음"}, {"category": "감정형", "keyword": "안심"}]'::jsonb,
  '{"totalScore": 65, "safetyLevel": "안전", "categoryScores": {"naturalSurveillance": 30, "activitySupport": 20, "emotional": 15}}'::jsonb,
  'restricted'
),
(
  gen_random_uuid()::text,
  '골목길이 많고 복잡해서 길을 잃을까 봐 걱정돼요',
  '마포구 홍대동',
  '저녁',
  3,
  '[{"category": "자연적 접근 통제", "keyword": "골목많음"}, {"category": "자연적 접근 통제", "keyword": "복잡"}, {"category": "감정형", "keyword": "약간불안"}]'::jsonb,
  '{"totalScore": -10, "safetyLevel": "보통", "categoryScores": {"accessControl": -5, "emotional": -5}}'::jsonb,
  'gpt'
)
ON CONFLICT (id) DO NOTHING;