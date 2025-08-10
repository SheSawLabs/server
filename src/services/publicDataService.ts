import * as fs from 'fs';
import * as path from 'path';

export interface PublicSafetyData {
  dong_code: string;
  district: string;
  dong: string;
  grade: string;
  score: number;
  coordinates: {
    lat: number;
    lng: number;
  };
  facilities: {
    cctv: number;
    streetlight: number;
    police_station: number;
    safety_house: number;
    delivery_box: number;
  };
  risk_factors: {
    sexual_offender: number;
  };
}

export interface CPTEDFactors {
  natural_surveillance: number;  // CCTV + 가로등
  access_control: number;        // 성범죄자 관리
  territoriality: number;        // 경찰서 + 안심지킴이집
  maintenance: number;           // 기본값 (실제 데이터 부족)
  activity_support: number;      // 택배함 + 기본값
}

export class PublicDataService {
  private static safetyData: PublicSafetyData[] | null = null;

  static loadSafetyData(): PublicSafetyData[] {
    if (this.safetyData) {
      return this.safetyData;
    }

    try {
      const dataPath = path.join('/home/rem/shesaw/safety_data_project/data/map_data.json');
      const rawData = fs.readFileSync(dataPath, 'utf-8');
      const jsonData = JSON.parse(rawData);
      
      this.safetyData = jsonData.data || [];
      return this.safetyData || [];
    } catch (error) {
      console.error('Failed to load safety data:', error);
      return [];
    }
  }

  static findByLocation(location: string): PublicSafetyData | null {
    const data = this.loadSafetyData();
    
    // 동 이름으로 검색
    const found = data.find(item => 
      item.dong.includes(location) || 
      location.includes(item.dong) ||
      item.district.includes(location) ||
      location.includes(item.district)
    );

    return found || null;
  }

  static analyzeCPTEDFactors(safetyData: PublicSafetyData): CPTEDFactors {
    const { facilities, risk_factors } = safetyData;

    return {
      // 자연적 감시: CCTV + 가로등 (높을수록 좋음)
      natural_surveillance: facilities.cctv + facilities.streetlight,
      
      // 접근통제: 성범죄자 수 (낮을수록 좋음, 역수 사용)
      access_control: risk_factors.sexual_offender,
      
      // 영역성 강화: 경찰서 + 안심지킴이집 (높을수록 좋음)
      territoriality: facilities.police_station + facilities.safety_house,
      
      // 유지관리: 기본값 (실제 데이터 부족)
      maintenance: 50, // 중간값
      
      // 활동성 지원: 택배함 등 (높을수록 좋음)
      activity_support: facilities.delivery_box
    };
  }

  static getKeywordRecommendationsByData(safetyData: PublicSafetyData): string[] {
    const factors = this.analyzeCPTEDFactors(safetyData);
    const recommendations: string[] = [];

    // 자연적 감시 관련
    if (factors.natural_surveillance >= 100) {
      recommendations.push('밝음');
    } else if (factors.natural_surveillance <= 20) {
      recommendations.push('어두움');
    }

    // 자연적 접근 통제 관련  
    if (factors.access_control >= 10) {
      recommendations.push('위험');
    } else if (factors.access_control <= 2) {
      recommendations.push('안심');
    }

    // 영역성 강화 관련
    if (factors.territoriality >= 10) {
      recommendations.push('깔끔');
    } else if (factors.territoriality <= 2) {
      recommendations.push('방치됨');
    }

    // 활동성 관련
    if (factors.activity_support >= 5) {
      recommendations.push('주요상권있음');
    }

    // 전체 안전도 기반 감정 키워드
    if (safetyData.grade === 'A' || safetyData.grade === 'B') {
      recommendations.push('안심');
    } else if (safetyData.grade === 'D' || safetyData.grade === 'E') {
      recommendations.push('불안');
    }

    return recommendations;
  }
}