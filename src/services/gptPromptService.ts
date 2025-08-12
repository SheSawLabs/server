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
    "조도 환경": ["밤에도 밝아요", "골목이 어두워요", "사각지대가 많아요", "공원•녹지가 잘 보이는 곳이에요"],
    "사람•활동": ["밤에도 사람 왕래가 많아요", "주변이 한산해요", "상점•편의점이 늦게까지 열어요", "배달•택배가 자주 보여요"],
    "치안•안전": ["순찰차가 자주 돌아요", "비상벨/안심비상을 봤어요", "복잡한 골목길이 많아요"],
    "생활 편의": ["편의점•마트가 많아요", "카페/음식점이 많아요", "늦게까지 여는 가게 있어요", "배달•택배가 편리해요"],
    "부정적 키워드": ["어두운 골목이 많아요", "유흥가가 많아요", "밤 늦게도 소음이 심해요", "밤에 술 취한 사람이 많아요"]
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

**사용 가능한 키워드 목록:**
- 조도 환경: 
  * 밤에도 밝아요 (조명이 좋음, 가로등이 많음, 환함)
  * 골목이 어두워요 (어둠, 조명 부족, 가로등 없음)
  * 사각지대가 많아요 (보이지 않는 곳, 막힌 곳, 시야 차단)
  * 공원•녹지가 잘 보이는 곳이에요 (개방적, 시야 좋음, 탁 트임)
- 사람•활동: 
  * 밤에도 사람 왕래가 많아요 (인적이 많음, 활발함, 붐빔)
  * 주변이 한산해요 (조용함, 인적 드뭄, 한적함)
  * 상점•편의점이 늦게까지 열어요 (야간 영업, 24시간, 늦은 시간)
  * 배달•택배가 자주 보여요 (배송 활발, 물류 많음, 택배차)
- 치안•안전: 
  * 순찰차가 자주 돌아요 (경찰 순찰, 치안 좋음, 안전 관리)
  * 비상벨/안심비상을 봤어요 (안전 시설, 비상 대비, 안심 시설)
  * 복잡한 골목길이 많아요 (미로 같음, 복잡한 길, 샛길)
- 생활 편의: 
  * 편의점•마트가 많아요 (상권 발달, 쇼핑 편리, 생활 시설)
  * 카페/음식점이 많아요 (외식업 많음, 맛집, 다양한 음식점)
  * 늦게까지 여는 가게 있어요 (야간 영업, 심야 운영, 24시간)
  * 배달•택배가 편리해요 (배송 편리, 접근성 좋음, 물류 원활)
- 부정적 키워드: 
  * 어두운 골목이 많아요 (위험한 길, 음침함, 어두운 곳)
  * 유흥가가 많아요 (술집, 클럽, 유흥업소)
  * 밤 늦게도 소음이 심해요 (시끄러움, 소음 공해, 불쾌함)
  * 밤에 술 취한 사람이 많아요 (음주자, 취객, 위험 요소)

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