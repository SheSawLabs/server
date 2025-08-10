const request = require('supertest');
const app = require('../src/app').default;

describe('제한적 CPTED 분석 시스템 테스트', () => {
  
  // 시스템 정보 조회 테스트
  describe('GET /api/restricted/system-info', () => {
    test('시스템 정보가 올바르게 반환되는지 확인', async () => {
      const response = await request(app)
        .get('/api/restricted/system-info')
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.data.system.analysisMethod).toBe('restricted');
      expect(response.body.data.availableKeywords).toBeDefined();
      expect(response.body.data.totalKeywords).toBeGreaterThan(0);
    });
  });

  // 제한적 분석 API 테스트
  describe('POST /api/restricted/analyze-restricted', () => {
    test('정상적인 리뷰 텍스트 분석', async () => {
      const testData = {
        reviewText: '밤에 이 길을 걸으면 가로등이 부족해서 너무 어둡고 무서워요. CCTV도 별로 없는 것 같고.',
        location: '강남구 역삼동',
        timeOfDay: '밤',
        rating: 2
      };

      const response = await request(app)
        .post('/api/restricted/analyze-restricted')
        .send(testData)
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.method).toBe('restricted');
      expect(response.body.data.recommendedKeywords).toBeDefined();
      expect(response.body.data.scoreResult).toBeDefined();
      expect(response.body.data.contextAnalysis).toBeDefined();
      
      // 어둡다는 키워드가 감지되었는지 확인
      const hasLightingKeyword = response.body.data.recommendedKeywords.some(k => 
        k.keyword === '어두움' || k.keyword === '밝음'
      );
      expect(hasLightingKeyword).toBe(true);
    });

    test('빈 텍스트 입력 시 오류 처리', async () => {
      const response = await request(app)
        .post('/api/restricted/analyze-restricted')
        .send({ reviewText: '' })
        .expect(400);

      expect(response.body.success).toBe(false);
      expect(response.body.error).toContain('리뷰 텍스트가 필요합니다');
    });

    test('너무 긴 텍스트 입력 시 경고 처리', async () => {
      const longText = 'a'.repeat(1001);
      const response = await request(app)
        .post('/api/restricted/analyze-restricted')
        .send({ reviewText: longText })
        .expect(400);

      expect(response.body.success).toBe(false);
      expect(response.body.details).toBeDefined();
    });
  });

  // 키워드 기반 분석 테스트
  describe('POST /api/restricted/analyze-keywords', () => {
    test('키워드만으로 분석', async () => {
      const testData = {
        selectedKeywords: [
          { category: 'naturalSurveillance', keyword: '어두움' },
          { category: 'emotional', keyword: '불안' }
        ],
        location: '강남구 역삼동',
        timeOfDay: '밤',
        rating: 2
      };

      const response = await request(app)
        .post('/api/restricted/analyze-keywords')
        .send(testData)
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.method).toBe('keywords_only');
      expect(response.body.data.selectedKeywords).toBeDefined();
      expect(response.body.data.scoreResult).toBeDefined();
    });

    test('빈 키워드 배열 시 오류 처리', async () => {
      const response = await request(app)
        .post('/api/restricted/analyze-keywords')
        .send({ selectedKeywords: [] })
        .expect(400);

      expect(response.body.success).toBe(false);
      expect(response.body.error).toContain('선택된 키워드가 필요합니다');
    });
  });

  // 키워드 추천 API 테스트
  describe('POST /api/restricted/recommend-keywords', () => {
    test('텍스트에서 키워드 추천', async () => {
      const testData = {
        reviewText: '공원 근처라서 사람들이 많이 다니고 밝아서 안전해 보여요.',
        location: '강남구 역삼동'
      };

      const response = await request(app)
        .post('/api/restricted/recommend-keywords')
        .send(testData)
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.method).toBe('text_analysis_only');
      expect(response.body.data.recommendedKeywords).toBeDefined();
      
      // 긍정적인 키워드가 추천되었는지 확인
      const hasPositiveKeywords = response.body.data.recommendedKeywords.some(k => 
        k.keyword === '밝음' || k.keyword === '복잡' || k.keyword === '안심'
      );
      expect(hasPositiveKeywords).toBe(true);
    });
  });

  // 특수 케이스 테스트
  describe('특수 케이스 처리', () => {
    test('부정 표현 감지 ("밝지 않다" -> "어두움")', async () => {
      const testData = {
        reviewText: '이 길은 밝지 않고 깨끗하지도 않네요.',
      };

      const response = await request(app)
        .post('/api/restricted/recommend-keywords')
        .send(testData)
        .expect(200);

      expect(response.body.success).toBe(true);
      
      // 부정 표현이 올바르게 감지되었는지 확인
      const keywordNames = response.body.data.recommendedKeywords.map(k => k.keyword);
      expect(keywordNames).toContain('어두움');
    });

    test('공공데이터 기반 추천', async () => {
      const testData = {
        reviewText: '그냥 평범한 동네예요.',
        location: '강남구 역삼동', // 공공데이터가 있는 지역
        timeOfDay: '밤'
      };

      const response = await request(app)
        .post('/api/restricted/analyze-restricted')
        .send(testData)
        .expect(200);

      expect(response.body.success).toBe(true);
      
      // 공공데이터 기반 키워드가 포함되어야 함
      const publicDataKeywords = response.body.data.recommendedKeywords.filter(k => 
        k.source === 'public_data'
      );
      expect(publicDataKeywords.length).toBeGreaterThan(0);
    });
  });

  // 보안 테스트
  describe('보안 및 안전성 테스트', () => {
    test('개인정보 포함 텍스트 정화', async () => {
      const testData = {
        reviewText: '연락처는 010-1234-5678이고 이메일은 test@example.com입니다. 이 길은 어두워요.'
      };

      const response = await request(app)
        .post('/api/restricted/analyze-restricted')
        .send(testData)
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.data.reviewText).not.toContain('010-1234-5678');
      expect(response.body.data.reviewText).not.toContain('test@example.com');
    });

    test('부적절한 언어 필터링', async () => {
      const testData = {
        reviewText: '이 길은 정말 시발 어둡고 무서워'
      };

      const response = await request(app)
        .post('/api/restricted/analyze-restricted')
        .send(testData)
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.data.reviewText).not.toContain('시발');
      expect(response.body.data.preprocessResult.issues).toContain('부적절한 내용이 제거되었습니다.');
    });

    test('SQL 인젝션 시도 차단', async () => {
      const testData = {
        reviewText: "'; DROP TABLE users; -- 이 길은 어둡다"
      };

      const response = await request(app)
        .post('/api/restricted/analyze-restricted')
        .send(testData)
        .expect(200);

      expect(response.body.success).toBe(true);
      // SQL 구문은 제거되고 일반 텍스트만 남아야 함
      expect(response.body.data.reviewText).not.toContain('DROP TABLE');
    });
  });

  // 성능 테스트
  describe('성능 테스트', () => {
    test('응답 시간이 3초 이내인지 확인', async () => {
      const startTime = Date.now();
      
      const testData = {
        reviewText: '밤에 이 길을 걸으면 가로등이 부족해서 너무 어둡고 무서워요.',
        location: '강남구 역삼동',
        timeOfDay: '밤',
        rating: 2
      };

      const response = await request(app)
        .post('/api/restricted/analyze-restricted')
        .send(testData)
        .expect(200);

      const responseTime = Date.now() - startTime;
      expect(responseTime).toBeLessThan(3000); // 3초 이내
      expect(response.body.success).toBe(true);
    });
  });
});

describe('키워드 매칭 시스템 단위 테스트', () => {
  test('동의어 매칭 정확성', async () => {
    const testCases = [
      { text: '환하고 깨끗한 길', expectedKeywords: ['밝음', '깨끗'] },
      { text: '깜깜하고 지저분함', expectedKeywords: ['어두움', '쓰레기많음'] },
      { text: '사람이 많아서 복잡함', expectedKeywords: ['복잡'] },
      { text: '인적이 드물고 한적함', expectedKeywords: ['한적'] }
    ];

    for (const testCase of testCases) {
      const response = await request(app)
        .post('/api/restricted/recommend-keywords')
        .send({ reviewText: testCase.text })
        .expect(200);

      const keywordNames = response.body.data.recommendedKeywords.map(k => k.keyword);
      
      testCase.expectedKeywords.forEach(expectedKeyword => {
        expect(keywordNames).toContain(expectedKeyword);
      });
    }
  });
});