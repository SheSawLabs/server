import { PublicDataService } from './publicDataService';

export interface KeywordRecommendation {
  category: string;
  keyword: string;
  confidence: number;
  reason: string;
}

export interface GPTAnalysisResult {
  recommendedKeywords: KeywordRecommendation[];
  emotionalSummary: string;
  situationSummary: string;
}

export class GPTPromptService {
  private static readonly availableKeywords = {
    "자연적 감시": ["밝음", "어두움", "시야트임"],
    "자연적 접근 통제": ["한적", "복잡", "골목많음"],
    "영역성 강화": ["어수선", "깔끔", "방치됨"],
    "활동 활성화": ["주요상권있음", "공원있음"],
    "유지관리": ["깨끗", "쓰레기많음", "방치"],
    "감정형": ["안심", "약간불안", "불안", "위험"]
  } as const;

  static createKeywordRecommendationPrompt(reviewText: string, location?: string, timeOfDay?: string): string {
    const contextInfo = [];
    if (location) contextInfo.push(`위치: ${location}`);
    if (timeOfDay) contextInfo.push(`시간대: ${timeOfDay}`);
    
    // 공공데이터 기반 분석
    let publicDataContext = '';
    let publicDataRecommendations = '';
    
    if (location) {
      const safetyData = PublicDataService.findByLocation(location);
      if (safetyData) {
        const factors = PublicDataService.analyzeCPTEDFactors(safetyData);
        const dataRecommendations = PublicDataService.getKeywordRecommendationsByData(safetyData);
        
        publicDataContext = `
**공공데이터 기반 ${location} 지역 현황:**
- 안전도 등급: ${safetyData.grade}급 (점수: ${safetyData.score})
- CCTV: ${safetyData.facilities.cctv}개, 가로등: ${safetyData.facilities.streetlight}개
- 경찰서: ${safetyData.facilities.police_station}개, 안심지킴이집: ${safetyData.facilities.safety_house}개
- 성범죄자: ${safetyData.risk_factors.sexual_offender}명, 택배함: ${safetyData.facilities.delivery_box}개`;
        
        if (dataRecommendations.length > 0) {
          publicDataRecommendations = `
**공공데이터 기반 추천 키워드:** ${dataRecommendations.join(', ')}`;
        }
      }
    }

    const contextText = contextInfo.length > 0 ? `\n**맥락 정보:** ${contextInfo.join(', ')}` : '';

    return `당신은 CPTED(범죄예방환경설계) 분석 전문가입니다.
사용자가 입력한 동네/장소 리뷰${contextText ? '와 맥락 정보' : ''}를 분석하여, 다음 고정된 키워드 목록에서 해당하는 키워드들을 추천해주세요.

**사용 가능한 키워드 목록 (동의어 포함):**
- 자연적 감시: 
  * 밝음 (환함, 조명좋음, 불빛, 가로등, 밝다, 환하다)
  * 어두움 (깜깜함, 어둡다, 조명부족, 가로등없음, 캄캄하다)
  * 시야트임 (가림, 막힘, 보이지않음, 은밀함, 차단됨)
- 자연적 접근 통제: 
  * 한적 (외진, 인적드뭄, 조용함, 적막, 인적없음)
  * 복잡 (번화, 사람많음, 붐빔, 활기, 번잡함)
  * 골목많음 (미로같음, 복잡한길, 샛길, 뒷골목, 좁은길)
- 영역성 강화: 
  * 어수선 (지저분, 정리안됨, 난잡, 무질서, 복잡함)
  * 깔끔 (정돈됨, 깨끗, 단정, 정리됨, 체계적)
  * 방치됨 (버려짐, 관리안됨, 낙후, 폐허같음, 관리부족)
- 활동 활성화: 
  * 주요상권있음 (상가, 가게많음, 편의점, 카페, 상점)
  * 공원있음 (녹지, 운동시설, 놀이터, 산책로, 휴식공간)
- 유지관리: 
  * 깨끗 (청결, 위생적, 정돈, 관리잘됨)
  * 쓰레기많음 (더러움, 오염, 악취, 불결, 지저분)
  * 방치 (관리부족, 낙후, 노후, 수리필요)
- 감정형: 
  * 안심 (안전, 편안, 평화로움, 마음놓임)
  * 약간불안 (조금걱정, 살짝무서움, 신경쓰임, 약간걱정)
  * 불안 (걱정, 무서움, 두려움, 불편함)
  * 위험 (매우무서움, 극도불안, 공포, 위험함)

**분석할 리뷰:** "${reviewText}"${contextText}${publicDataContext}${publicDataRecommendations}

**분석 고려사항:**
- 공공데이터를 최우선으로 고려하여 객관적 키워드 추천
- CCTV/가로등 많음 → 밝음, 적음 → 어두움
- 성범죄자 많음 → 위험/불안, 적음 → 안심
- 경찰서/안심지킴이집 많음 → 깔끔, 적음 → 방치됨
- 안전도 등급 A/B → 안심, D/E → 불안/위험
- 늦은 시간(밤, 새벽): 조명과 감시 요소 중요도 증가

**응답 형식 (JSON):**
{
  "recommendedKeywords": [
    {
      "category": "자연적 감시",
      "keyword": "어두움",
      "confidence": 0.9,
      "reason": "가로등이 부족하다고 언급${timeOfDay === '밤' || timeOfDay === '새벽' ? ' + 늦은 시간대 특성상 조명 중요' : ''}"
    }
  ],
  "emotionalSummary": "전반적인 감정 상태 요약",
  "situationSummary": "장소의 상황 요약${contextText ? ' (맥락 정보 포함)' : ''}"
}

**분석 정확도 향상 지침:**
- 동의어와 비슷한 표현도 해당 키워드로 분류
- 문맥상 암시되는 내용도 고려 (예: "밤늦게 혼자 다니기 무서워" → 어두움, 불안)
- 부정 표현도 분석 (예: "밝지 않아" → 어두움, "깨끗하지 않네" → 쓰레기많음)
- 간접적 표현도 파악 (예: "CCTV가 많아" → 밝음, "사람이 없어" → 한적)

**추천 규칙:**
- 위 키워드 목록에서만 선택 (정확한 키워드명 사용)
- 공공데이터 기반 추천을 최우선 고려
- 리뷰 내용과 직간접적으로 관련 있는 키워드만 추천
- 동의어, 부정표현, 문맥적 암시 모두 고려
- confidence 0.7 이상만 추천
- 각 카테고리당 최대 1개 키워드만 추천
- 공공데이터와 리뷰 내용이 상반될 경우 공공데이터 우선`;
  }

  static getAvailableKeywords() {
    return this.availableKeywords;
  }
}