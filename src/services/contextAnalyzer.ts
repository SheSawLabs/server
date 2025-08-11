import { KeywordMatch } from './keywordMatcher';
import { PublicDataService } from './publicDataService';

export interface LocationContext {
  district: string;
  dong: string;
  safetyGrade: string;
  safetyScore: number;
  facilities: {
    cctv: number;
    streetlight: number;
    police_station: number;
    safety_house: number;
    delivery_box: number;
  };
  riskFactors: {
    sexual_offender: number;
  };
}

export interface TimeContext {
  period: 'morning' | 'afternoon' | 'evening' | 'night' | 'dawn';
  riskLevel: 'low' | 'medium' | 'high';
}

export interface ContextAnalysisResult {
  locationContext?: LocationContext;
  timeContext?: TimeContext;
  contextualKeywords: KeywordMatch[];
  riskAssessment: {
    overallRisk: 'low' | 'medium' | 'high';
    factors: string[];
    recommendations: string[];
  };
}

export class ContextAnalyzer {
  
  /**
   * 위치와 시간대 맥락을 종합하여 분석
   */
  analyzeContext(
    location?: string, 
    timeOfDay?: string, 
    existingKeywords: KeywordMatch[] = []
  ): ContextAnalysisResult {
    const locationContext = location ? this.analyzeLocation(location) : undefined;
    const timeContext = timeOfDay ? this.analyzeTime(timeOfDay) : undefined;
    
    const contextualKeywords = this.generateContextualKeywords(
      locationContext, 
      timeContext, 
      existingKeywords
    );
    
    const riskAssessment = this.assessRisk(locationContext, timeContext, existingKeywords);
    
    return {
      locationContext,
      timeContext,
      contextualKeywords,
      riskAssessment
    };
  }

  /**
   * 위치 정보 분석 (공공데이터 기반)
   */
  private analyzeLocation(location: string): LocationContext | undefined {
    const safetyData = PublicDataService.findByLocation(location);
    
    if (!safetyData) {
      return undefined;
    }
    
    return {
      district: safetyData.district,
      dong: safetyData.dong,
      safetyGrade: safetyData.grade,
      safetyScore: safetyData.score,
      facilities: safetyData.facilities,
      riskFactors: safetyData.risk_factors
    };
  }

  /**
   * 시간대 분석
   */
  private analyzeTime(timeOfDay: string): TimeContext {
    const timeValue = timeOfDay.toLowerCase();
    let period: TimeContext['period'];
    let riskLevel: TimeContext['riskLevel'];
    
    // 시간대별 분류
    if (timeValue.includes('아침') || timeValue.includes('오전') || timeValue.includes('morning')) {
      period = 'morning';
      riskLevel = 'low';
    } else if (timeValue.includes('오후') || timeValue.includes('낮') || timeValue.includes('afternoon')) {
      period = 'afternoon';
      riskLevel = 'low';
    } else if (timeValue.includes('저녁') || timeValue.includes('evening')) {
      period = 'evening';
      riskLevel = 'medium';
    } else if (timeValue.includes('밤') || timeValue.includes('야간') || timeValue.includes('night')) {
      period = 'night';
      riskLevel = 'high';
    } else if (timeValue.includes('새벽') || timeValue.includes('dawn')) {
      period = 'dawn';
      riskLevel = 'high';
    } else {
      period = 'afternoon'; // 기본값
      riskLevel = 'low';
    }
    
    return { period, riskLevel };
  }

  /**
   * 맥락 기반 키워드 생성
   */
  private generateContextualKeywords(
    locationContext?: LocationContext,
    timeContext?: TimeContext,
    existingKeywords: KeywordMatch[] = []
  ): KeywordMatch[] {
    const contextualKeywords: KeywordMatch[] = [];
    
    // 위치 기반 키워드 추가
    if (locationContext) {
      // CCTV 수 기반 조명 키워드
      if (locationContext.facilities.cctv < 5) {
        contextualKeywords.push({
          category: 'naturalSurveillance',
          categoryName: '자연적 감시',
          keyword: '어두움',
          confidence: 0.8,
          matchedText: '공공데이터: CCTV 부족',
          weight: -3,
          positiveImpact: false
        });
      } else if (locationContext.facilities.cctv > 15) {
        contextualKeywords.push({
          category: 'naturalSurveillance',
          categoryName: '자연적 감시',
          keyword: '밝음',
          confidence: 0.8,
          matchedText: '공공데이터: CCTV 충분',
          weight: 3,
          positiveImpact: true
        });
      }
      
      // 성범죄자 수 기반 안전도 키워드
      if (locationContext.riskFactors.sexual_offender > 10) {
        contextualKeywords.push({
          category: 'emotional',
          categoryName: '감정형',
          keyword: '위험',
          confidence: 0.9,
          matchedText: '공공데이터: 성범죄자 다수 거주',
          weight: -4,
          positiveImpact: false
        });
      } else if (locationContext.riskFactors.sexual_offender < 3) {
        contextualKeywords.push({
          category: 'emotional',
          categoryName: '감정형',
          keyword: '안심',
          confidence: 0.8,
          matchedText: '공공데이터: 성범죄자 적음',
          weight: 4,
          positiveImpact: true
        });
      }
      
      // 안전 시설 기반 키워드
      const totalSafetyFacilities = locationContext.facilities.police_station + 
                                  locationContext.facilities.safety_house;
      if (totalSafetyFacilities > 5) {
        contextualKeywords.push({
          category: 'territorialReinforcement',
          categoryName: '영역성 강화',
          keyword: '깔끔',
          confidence: 0.7,
          matchedText: '공공데이터: 안전시설 충분',
          weight: 3,
          positiveImpact: true
        });
      }
    }
    
    // 시간대 기반 키워드 강화
    if (timeContext && (timeContext.period === 'night' || timeContext.period === 'dawn')) {
      // 야간/새벽 시간대에는 조명 관련 키워드 가중치 증가
      const existingLightingKeyword = existingKeywords.find(k => 
        k.category === 'naturalSurveillance' && 
        (k.keyword === '어두움' || k.keyword === '밝음')
      );
      
      if (existingLightingKeyword) {
        // 기존 조명 관련 키워드의 신뢰도를 높임
        existingLightingKeyword.confidence = Math.min(1.0, existingLightingKeyword.confidence + 0.2);
      } else if (!locationContext || locationContext.facilities.streetlight < 10) {
        // 가로등이 부족하면 어두움 키워드 추가
        contextualKeywords.push({
          category: 'naturalSurveillance',
          categoryName: '자연적 감시',
          keyword: '어두움',
          confidence: 0.8,
          matchedText: '야간/새벽 시간대 + 가로등 부족',
          weight: -3,
          positiveImpact: false
        });
      }
    }
    
    return this.removeDuplicateKeywords(contextualKeywords, existingKeywords);
  }

  /**
   * 종합 위험도 평가
   */
  private assessRisk(
    locationContext?: LocationContext,
    timeContext?: TimeContext,
    existingKeywords: KeywordMatch[] = []
  ): ContextAnalysisResult['riskAssessment'] {
    let riskScore = 0;
    const factors: string[] = [];
    const recommendations: string[] = [];
    
    // 위치 기반 위험도
    if (locationContext) {
      if (locationContext.safetyGrade === 'E' || locationContext.safetyGrade === 'D') {
        riskScore += 3;
        factors.push('지역 안전등급이 낮음');
        recommendations.push('가급적 다른 경로 이용 권장');
      }
      
      if (locationContext.riskFactors.sexual_offender > 10) {
        riskScore += 2;
        factors.push('성범죄자 거주 다수');
        recommendations.push('혼자 다니지 말고 동행자와 함께 이동');
      }
      
      if (locationContext.facilities.cctv < 5) {
        riskScore += 1;
        factors.push('CCTV 부족');
        recommendations.push('잘 보이는 주요 도로 이용');
      }
    }
    
    // 시간대 기반 위험도
    if (timeContext) {
      if (timeContext.riskLevel === 'high') {
        riskScore += 2;
        factors.push('위험 시간대 (야간/새벽)');
        recommendations.push('불가피한 경우가 아니면 이동 자제');
      } else if (timeContext.riskLevel === 'medium') {
        riskScore += 1;
        factors.push('주의 시간대 (저녁)');
        recommendations.push('조명이 밝은 길 이용');
      }
    }
    
    // 키워드 기반 위험도
    existingKeywords.forEach(keyword => {
      if (!keyword.positiveImpact && Math.abs(keyword.weight) >= 3) {
        riskScore += 1;
        factors.push(`${keyword.keyword} 요소 존재`);
      }
    });
    
    // 전체 위험도 결정
    let overallRisk: 'low' | 'medium' | 'high';
    if (riskScore <= 2) {
      overallRisk = 'low';
      if (recommendations.length === 0) {
        recommendations.push('일반적인 주의사항 준수');
      }
    } else if (riskScore <= 4) {
      overallRisk = 'medium';
      recommendations.push('주변 상황 주의깊게 관찰');
    } else {
      overallRisk = 'high';
      recommendations.push('가능한 이동 자제 또는 대체 경로 이용');
    }
    
    return {
      overallRisk,
      factors,
      recommendations
    };
  }

  /**
   * 중복 키워드 제거 (카테고리별로 하나씩만)
   */
  private removeDuplicateKeywords(
    newKeywords: KeywordMatch[], 
    existingKeywords: KeywordMatch[]
  ): KeywordMatch[] {
    const existingCategories = new Set(existingKeywords.map(k => k.category));
    
    return newKeywords.filter(keyword => !existingCategories.has(keyword.category));
  }
}