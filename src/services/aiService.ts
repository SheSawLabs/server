import Groq from 'groq-sdk';
import { GPTPromptService, GPTAnalysisResult } from './gptPromptService';

export class AIService {
  private groq?: Groq;
  private initialized = false;

  constructor() {
    // 생성자에서는 초기화하지 않음 (환경변수가 아직 로드되지 않을 수 있음)
  }

  private initialize() {
    if (this.initialized) return;
    
    console.log('🔍 AI 환경변수 체크:');
    console.log('GROQ_API_KEY:', process.env.GROQ_API_KEY ? 'SET' : 'NOT SET');
    console.log('DISABLE_AI:', process.env.DISABLE_AI);
    
    if (!process.env.GROQ_API_KEY || process.env.DISABLE_AI === 'true') {
      console.warn('AI service disabled - using local analysis only');
      this.initialized = true;
      return;
    }
    
    this.groq = new Groq({
      apiKey: process.env.GROQ_API_KEY,
    });
    this.initialized = true;
    console.log('✅ AI service initialized successfully');
  }

  async analyzeReview(reviewText: string, location?: string, timeOfDay?: string): Promise<GPTAnalysisResult> {
    try {
      // 사용할 때 초기화
      this.initialize();
      
      if (!this.groq) {
        throw new Error('AI service not initialized');
      }
      
      const prompt = GPTPromptService.createKeywordRecommendationPrompt(reviewText, location, timeOfDay);
      
      const response = await Promise.race([
        this.groq.chat.completions.create({
          model: 'llama-3.1-8b-instant', // Groq의 빠른 모델
          messages: [
            {
              role: 'system',
              content: 'You are a CPTED (Crime Prevention Through Environmental Design) expert. Respond only in valid JSON format.'
            },
            {
              role: 'user',
              content: prompt
            }
          ],
          temperature: 0.3,
          max_tokens: 1000,
        }),
        new Promise((_, reject) => 
          setTimeout(() => reject(new Error('AI API timeout')), 10000) // 10초 타임아웃
        )
      ]) as any;

      const content = response.choices[0]?.message?.content;
      if (!content) {
        throw new Error('No response from AI');
      }

      // JSON 파싱 및 검증
      const result: GPTAnalysisResult = JSON.parse(content);
      
      // 기본 구조 검증
      if (!result.recommendedKeywords || !Array.isArray(result.recommendedKeywords)) {
        throw new Error('Invalid response format: missing recommendedKeywords array');
      }

      // 키워드 유효성 검증
      const availableKeywords = GPTPromptService.getAvailableKeywords();
      result.recommendedKeywords = result.recommendedKeywords.filter(item => {
        const categoryKeywords = availableKeywords[item.category as keyof typeof availableKeywords];
        return categoryKeywords && (categoryKeywords as readonly string[]).includes(item.keyword);
      });

      return result;

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      console.warn(`AI API 호출 실패: ${errorMessage} - 로컬 분석으로 fallback합니다.`);
      
      // 기본 응답 반환 (로컬 분석으로 대체 가능하다는 메시지)
      return {
        recommendedKeywords: [],
        emotionalSummary: 'AI API 사용 불가 - 제한적 분석(/api/restricted) 사용을 권장합니다.',
        situationSummary: '로컬 키워드 매칭 방식으로 분석 가능합니다.'
      };
    }
  }
}