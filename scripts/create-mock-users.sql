-- Mock Users 데이터 생성 스크립트
-- users 테이블에 테스트용 사용자 데이터를 생성합니다

INSERT INTO users (provider, provider_id, email, nickname) VALUES 
('kakao', 'test_provider_1', 'user1@test.com', '혜명'),
('kakao', 'test_provider_2', 'user2@test.com', '은아'),
('kakao', 'test_provider_3', 'user3@test.com', '서현'),
('kakao', 'test_provider_4', 'user4@test.com', '재영'),
('kakao', 'test_provider_5', 'user5@test.com', '민지'),
('kakao', 'test_provider_6', 'user6@test.com', '수빈'),
('kakao', 'test_provider_7', 'user7@test.com', '지우'),
('kakao', 'test_provider_8', 'user8@test.com', '하린'),
('kakao', 'test_provider_9', 'user9@test.com', '예은'),
('kakao', 'test_provider_10', 'user10@test.com', '다은'),
('kakao', 'test_provider_11', 'user11@test.com', '소영'),
('kakao', 'test_provider_12', 'user12@test.com', '유진')
ON CONFLICT (provider, provider_id) DO NOTHING;