import fs from 'fs';
import path from 'path';

interface KeywordInfo {
  keyword: string;
  weight: number;
  positiveImpact: boolean;
  synonyms: string[];
}

interface CPTEDCategory {
  name: string;
  description: string;
  keywords: KeywordInfo[];
}

interface CPTEDData {
  cptedCategories: {
    [key: string]: CPTEDCategory;
  };
}

export interface KeywordMatch {
  category: string;
  categoryName: string;
  keyword: string;
  confidence: number;
  matchedText: string;
  weight: number;
  positiveImpact: boolean;
}

export class KeywordMatcher {
  private cptedData: CPTEDData;
  
  constructor() {
    const dataPath = path.join(__dirname, '../../data/cpted-keywords.json');
    this.cptedData = JSON.parse(fs.readFileSync(dataPath, 'utf-8'));
  }

  /**
   * 리뷰 텍스트에서 사전 정의된 키워드만 매칭하여 추천
   */
  analyzeText(reviewText: string): KeywordMatch[] {
    const matches: KeywordMatch[] = [];
    const normalizedText = this.normalizeText(reviewText);
    
    // 각 카테고리별로 키워드 매칭
    Object.entries(this.cptedData.cptedCategories).forEach(([categoryKey, category]) => {
      category.keywords.forEach(keywordInfo => {
        const confidence = this.calculateKeywordConfidence(normalizedText, keywordInfo);
        
        if (confidence >= 0.7) { // 임계값 이상만 포함
          const matchedText = this.findMatchedText(normalizedText, keywordInfo);
          
          matches.push({
            category: categoryKey,
            categoryName: category.name,
            keyword: keywordInfo.keyword,
            confidence,
            matchedText,
            weight: keywordInfo.weight,
            positiveImpact: keywordInfo.positiveImpact
          });
        }
      });
    });

    // 카테고리별로 최고 점수 키워드만 반환
    return this.selectBestKeywordPerCategory(matches);
  }

  /**
   * 텍스트 정규화
   */
  private normalizeText(text: string): string {
    return text
      .toLowerCase()
      .replace(/[^\w\s가-힣]/g, ' ') // 특수문자 제거
      .replace(/\s+/g, ' ') // 공백 정규화
      .trim();
  }

  /**
   * 키워드와 동의어들의 신뢰도 계산
   */
  private calculateKeywordConfidence(text: string, keywordInfo: KeywordInfo): number {
    const allKeywords = [keywordInfo.keyword, ...keywordInfo.synonyms];
    let maxConfidence = 0;
    
    allKeywords.forEach(keyword => {
      const normalizedKeyword = this.normalizeText(keyword);
      
      // 정확한 매칭
      if (text.includes(normalizedKeyword)) {
        maxConfidence = Math.max(maxConfidence, 1.0);
        return;
      }
      
      // 부분 매칭 (키워드가 텍스트에 포함)
      const words = text.split(' ');
      const keywordWords = normalizedKeyword.split(' ');
      
      if (keywordWords.every(kw => words.some(w => w.includes(kw)))) {
        maxConfidence = Math.max(maxConfidence, 0.8);
      }
      
      // 부정 표현 감지 ("밝지 않다" -> "어두움")
      const negationPatterns = ['안', '않', '못', '없'];
      const isNegated = negationPatterns.some(neg => 
        text.includes(neg + normalizedKeyword) || 
        text.includes(normalizedKeyword + neg)
      );
      
      if (isNegated) {
        // 부정된 긍정 키워드 -> 반대 키워드로 매칭
        if (keywordInfo.positiveImpact) {
          maxConfidence = Math.max(maxConfidence, 0.7);
        }
      }
    });
    
    return maxConfidence;
  }

  /**
   * 매칭된 텍스트 부분 찾기
   */
  private findMatchedText(text: string, keywordInfo: KeywordInfo): string {
    const allKeywords = [keywordInfo.keyword, ...keywordInfo.synonyms];
    
    for (const keyword of allKeywords) {
      const normalizedKeyword = this.normalizeText(keyword);
      const index = text.indexOf(normalizedKeyword);
      if (index !== -1) {
        return text.substring(
          Math.max(0, index - 10), 
          Math.min(text.length, index + normalizedKeyword.length + 10)
        ).trim();
      }
    }
    
    return '';
  }

  /**
   * 카테고리별로 가장 높은 신뢰도의 키워드만 선택
   */
  private selectBestKeywordPerCategory(matches: KeywordMatch[]): KeywordMatch[] {
    const categoryMap = new Map<string, KeywordMatch>();
    
    matches.forEach(match => {
      const existing = categoryMap.get(match.category);
      if (!existing || match.confidence > existing.confidence) {
        categoryMap.set(match.category, match);
      }
    });
    
    return Array.from(categoryMap.values())
      .sort((a, b) => b.confidence - a.confidence);
  }

  /**
   * 사용 가능한 모든 키워드 반환
   */
  getAvailableKeywords(): { [category: string]: string[] } {
    const result: { [category: string]: string[] } = {};
    
    Object.entries(this.cptedData.cptedCategories).forEach(([key, category]) => {
      result[category.name] = category.keywords.map(k => k.keyword);
    });
    
    return result;
  }
}