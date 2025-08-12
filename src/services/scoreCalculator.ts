export interface SelectedKeyword {
  category: string;
  keyword: string;
}

export interface CPTEDScores {
  naturalSurveillance: number;    // 자연적 감시 - 35%
  accessControl: number;          // 접근통제 - 25%
  territoriality: number;         // 영역성 강화 - 20%
  maintenance: number;            // 유지관리 - 10%
  activitySupport: number;        // 활동성 - 10%
}

export interface ScoreCalculationResult {
  totalScore: number;
  cptedScores: CPTEDScores;
  categoryScores: {
    [category: string]: {
      score: number;
      selectedKeywords: string[];
      keywordCounts: { [keyword: string]: number };
    };
  };
  grade: 'A' | 'B' | 'C' | 'D' | 'E';
  rating: number;
}

export class ScoreCalculator {
  // CPTED 원칙별 가중치 (Python 코드 참고)
  private static readonly CPTED_WEIGHTS = {
    naturalSurveillance: 0.35,    // 자연적 감시
    accessControl: 0.25,          // 접근통제
    territoriality: 0.20,         // 영역성 강화
    maintenance: 0.10,            // 유지관리
    activitySupport: 0.10         // 활동성
  } as const;

  // 새로운 키워드 → CPTED 원칙 매핑 및 점수
  private static readonly keywordToCPTED = {
    // 조도 환경
    "밤에도 밝아요": { principle: "naturalSurveillance", score: 30 },
    "골목이 어두워요": { principle: "naturalSurveillance", score: -30 },
    "사각지대가 많아요": { principle: "naturalSurveillance", score: -25 },
    "공원•녹지가 잘 보이는 곳이에요": { principle: "naturalSurveillance", score: 20 },
    
    // 사람•활동
    "밤에도 사람 왕래가 많아요": { principle: "activitySupport", score: 25 },
    "주변이 한산해요": { principle: "activitySupport", score: -20 },
    "상점•편의점이 늦게까지 열어요": { principle: "activitySupport", score: 30 },
    "배달•택배가 자주 보여요": { principle: "activitySupport", score: 15 },
    
    // 치안•안전
    "순찰차가 자주 돌아요": { 
      principle: "multiple", 
      scores: {
        naturalSurveillance: 25,
        accessControl: 20,
        territoriality: 15
      }
    },
    "비상벨/안심비상을 봤어요": { principle: "naturalSurveillance", score: 25 },
    "복잡한 골목길이 많아요": { principle: "accessControl", score: -20 },
    
    // 생활 편의
    "편의점•마트가 많아요": { principle: "activitySupport", score: 25 },
    "카페/음식점이 많아요": { principle: "activitySupport", score: 20 },
    "늦게까지 여는 가게 있어요": { principle: "activitySupport", score: 30 },
    "배달•택배가 편리해요": { principle: "activitySupport", score: 15 },
    
    // 부정적 키워드
    "어두운 골목이 많아요": { 
      principle: "multiple", 
      scores: {
        naturalSurveillance: -30,
        accessControl: -20,
        territoriality: -15
      }
    },
    "유흥가가 많아요": { 
      principle: "multiple", 
      scores: {
        territoriality: -25,
        maintenance: -20,
        accessControl: -15
      }
    },
    "밤 늦게도 소음이 심해요": { 
      principle: "multiple", 
      scores: {
        territoriality: -20,
        maintenance: -15
      }
    },
    "밤에 술 취한 사람이 많아요": { 
      principle: "multiple", 
      scores: {
        naturalSurveillance: -25,
        accessControl: -20,
        territoriality: -25
      }
    }
  } as const;

  // 안전도 등급 기준 (Python 코드 참고)
  private static readonly GRADE_THRESHOLDS = {
    'A': 60.0,   // 매우 안전
    'B': 50.0,   // 안전
    'C': 40.0,   // 보통
    'D': 30.0,   // 위험
    'E': 0.0     // 매우 위험
  } as const;

  static calculateScore(selectedKeywords: SelectedKeyword[], rating: number = 3): ScoreCalculationResult {
    // CPTED 원칙별 점수 초기화 (별점 기반)
    const baseScore = rating * 20; // 1점=20, 2점=40, 3점=60, 4점=80, 5점=100
    const cptedScores: CPTEDScores = {
      naturalSurveillance: baseScore,
      accessControl: baseScore,
      territoriality: baseScore,
      maintenance: baseScore,
      activitySupport: baseScore
    };

    // 카테고리별 점수 및 키워드 카운트 추적
    const categoryScores: { [category: string]: { score: number; selectedKeywords: string[]; keywordCounts: { [keyword: string]: number } } } = {
      "자연적 감시": { score: 0, selectedKeywords: [], keywordCounts: {} },
      "자연적 접근 통제": { score: 0, selectedKeywords: [], keywordCounts: {} },
      "영역성 강화": { score: 0, selectedKeywords: [], keywordCounts: {} },
      "활동 활성화": { score: 0, selectedKeywords: [], keywordCounts: {} },
      "유지관리": { score: 0, selectedKeywords: [], keywordCounts: {} },
      "감정형": { score: 0, selectedKeywords: [], keywordCounts: {} }
    };

    // 키워드 카운트 계산
    selectedKeywords.forEach(({ category, keyword }) => {
      if (categoryScores[category]) {
        categoryScores[category].keywordCounts[keyword] = 
          (categoryScores[category].keywordCounts[keyword] || 0) + 1;
        
        if (!categoryScores[category].selectedKeywords.includes(keyword)) {
          categoryScores[category].selectedKeywords.push(keyword);
        }
      }
    });

    // 선택된 키워드로 점수 조정
    selectedKeywords.forEach(({ category, keyword }) => {
      const keywordData = this.keywordToCPTED[keyword as keyof typeof this.keywordToCPTED];
      
      if (!keywordData) {
        console.warn(`키워드 매핑을 찾을 수 없습니다: ${keyword}`);
        return;
      }

      // categoryScores가 존재하는지 확인
      if (!categoryScores[category]) {
        console.warn(`카테고리를 찾을 수 없습니다: ${category}`);
        return;
      }

      if (keywordData.principle === "multiple") {
        // 감정형 키워드 - 여러 CPTED 원칙에 영향
        const scores = keywordData.scores as any;
        if (scores) {
          Object.keys(scores).forEach(principle => {
            if (cptedScores[principle as keyof CPTEDScores] !== undefined) {
              cptedScores[principle as keyof CPTEDScores] += scores[principle];
              categoryScores[category].score += scores[principle];
            }
          });
        }
      } else {
        // 단일 원칙에 영향
        const principle = keywordData.principle as keyof CPTEDScores;
        const score = (keywordData as any).score;
        
        if (score !== undefined && cptedScores[principle] !== undefined) {
          cptedScores[principle] += score;
          categoryScores[category].score += score;
        }
      }
    });

    // CPTED 점수 범위 제한 (0-100)
    Object.keys(cptedScores).forEach(key => {
      const principle = key as keyof CPTEDScores;
      cptedScores[principle] = Math.max(0, Math.min(100, cptedScores[principle]));
    });

    // CPTED 가중치 적용하여 총점 계산
    const totalScore = 
      cptedScores.naturalSurveillance * this.CPTED_WEIGHTS.naturalSurveillance +
      cptedScores.accessControl * this.CPTED_WEIGHTS.accessControl +
      cptedScores.territoriality * this.CPTED_WEIGHTS.territoriality +
      cptedScores.maintenance * this.CPTED_WEIGHTS.maintenance +
      cptedScores.activitySupport * this.CPTED_WEIGHTS.activitySupport;

    // 등급 결정
    const grade = this.getSafetyGrade(totalScore);

    return {
      totalScore: Math.round(totalScore * 100) / 100,
      cptedScores: {
        naturalSurveillance: Math.round(cptedScores.naturalSurveillance * 100) / 100,
        accessControl: Math.round(cptedScores.accessControl * 100) / 100,
        territoriality: Math.round(cptedScores.territoriality * 100) / 100,
        maintenance: Math.round(cptedScores.maintenance * 100) / 100,
        activitySupport: Math.round(cptedScores.activitySupport * 100) / 100
      },
      categoryScores,
      rating,
      grade
    };
  }


  private static getSafetyGrade(score: number): 'A' | 'B' | 'C' | 'D' | 'E' {
    for (const [grade, threshold] of Object.entries(this.GRADE_THRESHOLDS)) {
      if (score >= threshold) {
        return grade as 'A' | 'B' | 'C' | 'D' | 'E';
      }
    }
    return 'E';
  }

  static getKeywordMapping() {
    return this.keywordToCPTED;
  }

  static getCPTEDWeights() {
    return this.CPTED_WEIGHTS;
  }
}