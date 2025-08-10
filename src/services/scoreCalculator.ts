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

  // 키워드 → CPTED 원칙 매핑 및 점수
  private static readonly keywordToCPTED = {
    // 자연적 감시 관련
    "밝음": { principle: "naturalSurveillance", score: 30 },
    "어두움": { principle: "naturalSurveillance", score: -30 },
    "시야트임": { principle: "naturalSurveillance", score: -20 },
    
    // 접근통제 관련
    "한적": { principle: "accessControl", score: -20 },
    "복잡": { principle: "accessControl", score: 10 },
    "골목많음": { principle: "accessControl", score: -15 },
    
    // 영역성 강화 관련
    "어수선": { principle: "territoriality", score: -20 },
    "깔끔": { principle: "territoriality", score: 25 },
    "방치됨": { principle: "territoriality", score: -30 },
    
    // 활동성 관련
    "주요상권있음": { principle: "activitySupport", score: 30 },
    "공원있음": { principle: "activitySupport", score: 20 },
    
    // 유지관리 관련
    "깨끗": { principle: "maintenance", score: 25 },
    "쓰레기많음": { principle: "maintenance", score: -30 },
    "방치": { principle: "maintenance", score: -20 },
    
    // 감정형 (여러 원칙에 영향)
    "안심": { 
      principle: "multiple", 
      scores: {
        naturalSurveillance: 15,
        accessControl: 15,
        territoriality: 10
      }
    },
    "약간불안": { 
      principle: "multiple", 
      scores: {
        naturalSurveillance: -5,
        accessControl: -5,
        territoriality: -5
      }
    },
    "불안": { 
      principle: "multiple", 
      scores: {
        naturalSurveillance: -15,
        accessControl: -15,
        territoriality: -10
      }
    },
    "위험": { 
      principle: "multiple", 
      scores: {
        naturalSurveillance: -25,
        accessControl: -25,
        territoriality: -15
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