export class TextPreprocessor {
  
  /**
   * 텍스트 전처리 (정화, 정규화, 토큰화)
   */
  static preprocess(text: string): {
    original: string;
    cleaned: string;
    normalized: string;
    tokens: string[];
    isValid: boolean;
    issues: string[];
  } {
    const original = text;
    const issues: string[] = [];
    
    // 1. 기본 검증
    if (!text || typeof text !== 'string') {
      return {
        original,
        cleaned: '',
        normalized: '',
        tokens: [],
        isValid: false,
        issues: ['텍스트가 제공되지 않았습니다.']
      };
    }
    
    // 2. 길이 검증
    if (text.length > 1000) {
      issues.push('텍스트가 1000자를 초과합니다.');
    }
    
    if (text.trim().length < 5) {
      issues.push('텍스트가 너무 짧습니다.');
    }
    
    // 3. 텍스트 정화 (악성 내용 필터링)
    const cleaned = this.cleanText(text);
    if (cleaned !== text) {
      issues.push('부적절한 내용이 제거되었습니다.');
    }
    
    // 4. 정규화
    const normalized = this.normalizeText(cleaned);
    
    // 5. 토큰화
    const tokens = this.tokenize(normalized);
    
    const isValid = issues.filter(issue => 
      !issue.includes('부적절한 내용') // 정화된 경우는 유효로 간주
    ).length === 0 && tokens.length > 0;
    
    return {
      original,
      cleaned,
      normalized,
      tokens,
      isValid,
      issues
    };
  }

  /**
   * 텍스트 정화 (욕설, 비방, 개인정보 등 제거)
   */
  private static cleanText(text: string): string {
    let cleaned = text;
    
    // 개인정보 패턴 제거 (전화번호, 이메일 등)
    const phonePattern = /\b\d{2,3}[-\s]?\d{3,4}[-\s]?\d{4}\b/g;
    const emailPattern = /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/g;
    
    cleaned = cleaned.replace(phonePattern, '[전화번호]');
    cleaned = cleaned.replace(emailPattern, '[이메일]');
    
    // 욕설 및 비방 표현 필터링 (기본적인 패턴만)
    const inappropriatePatterns = [
      /\b(시발|씨발|좆|병신|새끼)\b/gi,
      /\b(죽어|꺼져|닥쳐)\b/gi
    ];
    
    inappropriatePatterns.forEach(pattern => {
      cleaned = cleaned.replace(pattern, '[부적절한표현]');
    });
    
    return cleaned;
  }

  /**
   * 텍스트 정규화
   */
  private static normalizeText(text: string): string {
    return text
      .toLowerCase() // 소문자 변환
      .replace(/[^\w\s가-힣]/g, ' ') // 특수문자를 공백으로 변환
      .replace(/\s+/g, ' ') // 연속된 공백을 하나로
      .trim(); // 앞뒤 공백 제거
  }

  /**
   * 토큰화 (의미있는 단어/구문 단위로 분할)
   */
  private static tokenize(text: string): string[] {
    // 공백으로 분할한 후 의미있는 토큰만 선택
    const tokens = text.split(' ')
      .filter(token => token.length > 1) // 1글자 단어 제외
      .filter(token => !this.isStopWord(token)) // 불용어 제외
      .map(token => token.trim())
      .filter(token => token.length > 0);
    
    return [...new Set(tokens)]; // 중복 제거
  }

  /**
   * 불용어 판단
   */
  private static isStopWord(word: string): boolean {
    const stopWords = [
      '은', '는', '이', '가', '을', '를', '에', '에서', '로', '으로',
      '과', '와', '의', '도', '만', '까지', '부터', '보다', '처럼',
      '그리고', '하지만', '그런데', '그래서', '또한', '그래도',
      '아', '어', '오', '우', '음', '그', '저', '이거', '그거', '저거',
      '것', '거', '게', '것들', '거들', '게들',
      'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'
    ];
    
    return stopWords.includes(word);
  }

  /**
   * 감정 표현 추출
   */
  static extractEmotionalExpressions(text: string): {
    positive: string[];
    negative: string[];
    neutral: string[];
  } {
    const positive: string[] = [];
    const negative: string[] = [];
    const neutral: string[] = [];
    
    const positivePatterns = [
      /\b(좋|안전|편안|깨끗|밝|환|넓|쾌적|만족)\w*/g,
      /\b(beautiful|safe|clean|bright|good|nice|comfortable)\w*/gi
    ];
    
    const negativePatterns = [
      /\b(나쁘|무서|어두|더러|좁|불안|위험|걱정|두려)\w*/g,
      /\b(bad|scary|dark|dirty|narrow|dangerous|worried|afraid)\w*/gi
    ];
    
    positivePatterns.forEach(pattern => {
      const matches = text.match(pattern);
      if (matches) positive.push(...matches);
    });
    
    negativePatterns.forEach(pattern => {
      const matches = text.match(pattern);
      if (matches) negative.push(...matches);
    });
    
    return { positive, negative, neutral };
  }

  /**
   * 위치 정보 추출
   */
  static extractLocationInfo(text: string): string[] {
    const locationPatterns = [
      /\b\w+구\b/g, // ~구
      /\b\w+동\b/g, // ~동
      /\b\w+로\b/g, // ~로
      /\b\w+길\b/g, // ~길
      /\b\w+역\b/g, // ~역
      /\b\w+공원\b/g, // ~공원
      /\b\w+학교\b/g, // ~학교
      /\b\w+시장\b/g  // ~시장
    ];
    
    const locations: string[] = [];
    
    locationPatterns.forEach(pattern => {
      const matches = text.match(pattern);
      if (matches) {
        locations.push(...matches);
      }
    });
    
    return [...new Set(locations)]; // 중복 제거
  }

  /**
   * 시간 정보 추출
   */
  static extractTimeInfo(text: string): string[] {
    const timePatterns = [
      /\b(아침|오전|낮|오후|저녁|밤|새벽|야간)\b/g,
      /\b\d{1,2}시\b/g, // ~시
      /\b(morning|afternoon|evening|night|dawn)\b/gi
    ];
    
    const times: string[] = [];
    
    timePatterns.forEach(pattern => {
      const matches = text.match(pattern);
      if (matches) {
        times.push(...matches);
      }
    });
    
    return [...new Set(times)]; // 중복 제거
  }
}