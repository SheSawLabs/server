import { Request, Response } from 'express';
import { KeywordMatcher, KeywordMatch } from '../services/keywordMatcher';
import { ContextAnalyzer, ContextAnalysisResult } from '../services/contextAnalyzer';
import { TextPreprocessor } from '../services/textPreprocessor';
import { ScoreCalculator, SelectedKeyword } from '../services/scoreCalculator';
import { ReviewService } from '../services/reviewService';

export class RestrictedReviewController {
  private keywordMatcher: KeywordMatcher;
  private contextAnalyzer: ContextAnalyzer;

  constructor() {
    this.keywordMatcher = new KeywordMatcher();
    this.contextAnalyzer = new ContextAnalyzer();
  }

  /**
   * 제한적 AI 분석 - 사전 정의된 키워드에서만 추천
   */
  async analyzeReviewRestricted(req: Request, res: Response) {
    try {
      const { reviewText, location, timeOfDay, rating } = req.body;

      // 1. 입력 검증
      if (!reviewText || typeof reviewText !== 'string') {
        return res.status(400).json({
          success: false,
          error: '리뷰 텍스트가 필요합니다.'
        });
      }

      // 2. 텍스트 전처리
      const preprocessResult = TextPreprocessor.preprocess(reviewText);
      
      if (!preprocessResult.isValid) {
        return res.status(400).json({
          success: false,
          error: '텍스트 처리 중 문제가 발생했습니다.',
          details: preprocessResult.issues
        });
      }

      // 3. 키워드 매칭 (사전 정의된 키워드에서만)
      const matchedKeywords = this.keywordMatcher.analyzeText(preprocessResult.normalized);

      // 4. 맥락 분석 (위치, 시간대)
      const contextAnalysis = this.contextAnalyzer.analyzeContext(
        location, 
        timeOfDay, 
        matchedKeywords
      );

      // 5. 최종 키워드 선택 (텍스트 매칭 + 맥락 키워드)
      const finalKeywords = this.mergeKeywords(matchedKeywords, contextAnalysis.contextualKeywords);

      // 6. 점수 계산 (키워드 + 별점)
      const selectedKeywords: SelectedKeyword[] = finalKeywords.map(k => ({
        category: k.category,
        keyword: k.keyword
      }));

      const scoreResult = rating 
        ? ScoreCalculator.calculateScore(selectedKeywords, rating)
        : ScoreCalculator.calculateScore(selectedKeywords);

      // 7. 감정 및 위치 정보 추출
      const emotionalExpressions = TextPreprocessor.extractEmotionalExpressions(reviewText);
      const locationInfo = TextPreprocessor.extractLocationInfo(reviewText);
      const timeInfo = TextPreprocessor.extractTimeInfo(reviewText);

      // 8. DB에 리뷰 저장
      let savedReviewId = null;
      try {
        const savedReview = await ReviewService.createReview({
          reviewText: preprocessResult.cleaned,
          location: location || undefined,
          timeOfDay: timeOfDay || undefined,
          rating: rating || undefined,
          selectedKeywords: selectedKeywords,
          recommendedKeywords: finalKeywords.map(k => ({
            category: k.categoryName,
            keyword: k.keyword,
            confidence: k.confidence,
            reason: k.matchedText
          })),
          scoreResult: {
            totalScore: scoreResult.totalScore,
            categoryScores: Object.entries(scoreResult.categoryScores).reduce((acc, [key, value]) => {
              acc[key] = (value as any).score;
              return acc;
            }, {} as { [key: string]: number }),
            safetyLevel: this.getScoreLevel(scoreResult.totalScore),
            recommendations: this.getRecommendations(scoreResult)
          },
          contextAnalysis: {
            ...contextAnalysis,
            emotionalExpressions,
            locationInfo,
            timeInfo,
            preprocessResult
          },
          analysisMethod: 'restricted'
        });
        savedReviewId = savedReview.id;
      } catch (dbError) {
        console.error('DB 저장 실패:', dbError);
      }

      res.json({
        success: true,
        method: 'restricted', // GPT 대신 제한적 방식 사용
        data: {
          // 저장된 리뷰 ID
          reviewId: savedReviewId,
          
          // 입력 정보
          reviewText: preprocessResult.cleaned,
          location: location || '',
          timeOfDay: timeOfDay || '',
          rating: rating || null,
          
          // 분석 결과
          preprocessResult: {
            isValid: preprocessResult.isValid,
            issues: preprocessResult.issues,
            tokens: preprocessResult.tokens
          },
          
          // 추천 키워드 (사전 정의된 것만)
          recommendedKeywords: finalKeywords.map(k => ({
            category: k.categoryName,
            keyword: k.keyword,
            confidence: k.confidence,
            reason: k.matchedText,
            source: k.matchedText.includes('공공데이터') ? 'public_data' : 'text_analysis',
            weight: k.weight,
            positiveImpact: k.positiveImpact
          })),
          
          // 점수 계산
          scoreResult,
          
          // 맥락 분석
          contextAnalysis: {
            locationContext: contextAnalysis.locationContext,
            timeContext: contextAnalysis.timeContext,
            riskAssessment: contextAnalysis.riskAssessment
          },
          
          // 추가 정보
          extractedInfo: {
            emotions: emotionalExpressions,
            locations: locationInfo,
            timeReferences: timeInfo
          },
          
          // 사용 가능한 키워드 목록
          availableKeywords: this.keywordMatcher.getAvailableKeywords()
        }
      });
      return;

    } catch (error) {
      console.error('Error in analyzeReviewRestricted:', error);
      return res.status(500).json({
        success: false,
        error: '제한적 분석 중 오류가 발생했습니다.'
      });
    }
  }

  /**
   * 키워드 기반 분석 (텍스트 없이 키워드만으로)
   */
  async analyzeByKeywordsOnly(req: Request, res: Response) {
    try {
      const { selectedKeywords, location, timeOfDay, rating } = req.body;

      // 입력 검증
      if (!selectedKeywords || !Array.isArray(selectedKeywords) || selectedKeywords.length === 0) {
        return res.status(400).json({
          success: false,
          error: '선택된 키워드가 필요합니다.'
        });
      }

      // 키워드 유효성 검증
      const availableKeywords = this.keywordMatcher.getAvailableKeywords();
      const validKeywords = selectedKeywords.filter(item => {
        const categoryKeywords = Object.values(availableKeywords).flat();
        return categoryKeywords.includes(item.keyword);
      });

      if (validKeywords.length === 0) {
        return res.status(400).json({
          success: false,
          error: '유효한 키워드가 없습니다.'
        });
      }

      // 맥락 분석
      const contextAnalysis = this.contextAnalyzer.analyzeContext(location, timeOfDay);

      // 점수 계산
      const scoreResult = rating 
        ? ScoreCalculator.calculateScore(validKeywords, rating)
        : ScoreCalculator.calculateScore(validKeywords);

      // DB에 리뷰 저장
      let savedReviewId = null;
      try {
        const savedReview = await ReviewService.createReview({
          reviewText: '', // 키워드만 선택한 경우 빈 문자열
          location: location || undefined,
          timeOfDay: timeOfDay || undefined,
          rating: rating || undefined,
          selectedKeywords: validKeywords,
          recommendedKeywords: contextAnalysis.contextualKeywords.map(k => ({
            category: k.categoryName,
            keyword: k.keyword,
            confidence: k.confidence,
            reason: k.matchedText || `${location ? '위치 ' : ''}${timeOfDay ? '시간대 ' : ''}맥락 분석 기반`
          })),
          scoreResult: {
            totalScore: scoreResult.totalScore,
            categoryScores: Object.entries(scoreResult.categoryScores).reduce((acc, [key, value]) => {
              acc[key] = (value as any).score;
              return acc;
            }, {} as { [key: string]: number }),
            safetyLevel: this.getScoreLevel(scoreResult.totalScore),
            recommendations: this.getRecommendations(scoreResult)
          },
          contextAnalysis: {
            ...contextAnalysis,
            keywordSelectionMethod: 'manual_only'
          },
          analysisMethod: 'keywords_only'
        });
        savedReviewId = savedReview.id;
      } catch (dbError) {
        console.error('키워드 분석 DB 저장 실패:', dbError);
      }

      res.json({
        success: true,
        method: 'keywords_only',
        data: {
          reviewId: savedReviewId,
          selectedKeywords: validKeywords,
          location: location || '',
          timeOfDay: timeOfDay || '',
          rating: rating || null,
          scoreResult,
          contextAnalysis: {
            locationContext: contextAnalysis.locationContext,
            timeContext: contextAnalysis.timeContext,
            riskAssessment: contextAnalysis.riskAssessment
          },
          availableKeywords
        }
      });
      return;

    } catch (error) {
      console.error('Error in analyzeByKeywordsOnly:', error);
      return res.status(500).json({
        success: false,
        error: '키워드 분석 중 오류가 발생했습니다.'
      });
    }
  }

  /**
   * 사용 가능한 키워드 및 시스템 정보 반환
   */
  async getSystemInfo(req: Request, res: Response) {
    try {
      const availableKeywords = this.keywordMatcher.getAvailableKeywords();
      const cptedWeights = ScoreCalculator.getCPTEDWeights();
      const keywordMapping = ScoreCalculator.getKeywordMapping();

      res.json({
        success: true,
        data: {
          system: {
            analysisMethod: 'restricted',
            description: '사전 정의된 CPTED 키워드만 사용하는 제한적 분석 시스템',
            features: [
              '공공데이터 기반 분석',
              '사전 정의된 키워드만 사용',
              '위치/시간대 맥락 분석',
              '텍스트 전처리 및 정화',
              '위험도 평가'
            ]
          },
          availableKeywords,
          cptedWeights,
          keywordMapping,
          totalKeywords: Object.values(availableKeywords).reduce((sum, arr) => sum + arr.length, 0),
          categories: Object.keys(availableKeywords).length
        }
      });
      return;

    } catch (error) {
      console.error('Error in getSystemInfo:', error);
      return res.status(500).json({
        success: false,
        error: '시스템 정보 조회 중 오류가 발생했습니다.'
      });
    }
  }

  /**
   * 텍스트만으로 키워드 추천 (GPT 없이)
   */
  async getKeywordRecommendationsOnly(req: Request, res: Response) {
    try {
      const { reviewText, location, timeOfDay } = req.body;

      if (!reviewText || typeof reviewText !== 'string') {
        return res.status(400).json({
          success: false,
          error: '리뷰 텍스트가 필요합니다.'
        });
      }

      // 텍스트 전처리
      const preprocessResult = TextPreprocessor.preprocess(reviewText);
      
      if (!preprocessResult.isValid) {
        return res.status(400).json({
          success: false,
          error: '텍스트 처리 중 문제가 발생했습니다.',
          details: preprocessResult.issues
        });
      }

      // 키워드 매칭
      const matchedKeywords = this.keywordMatcher.analyzeText(preprocessResult.normalized);

      // 맥락 분석
      const contextAnalysis = this.contextAnalyzer.analyzeContext(
        location, 
        timeOfDay, 
        matchedKeywords
      );

      // 최종 키워드
      const finalKeywords = this.mergeKeywords(matchedKeywords, contextAnalysis.contextualKeywords);

      res.json({
        success: true,
        method: 'text_analysis_only',
        data: {
          reviewText: preprocessResult.cleaned,
          recommendedKeywords: finalKeywords.map(k => ({
            category: k.categoryName,
            keyword: k.keyword,
            confidence: k.confidence,
            reason: k.matchedText,
            source: k.matchedText.includes('공공데이터') ? 'public_data' : 'text_analysis'
          })),
          contextAnalysis: {
            locationContext: contextAnalysis.locationContext,
            timeContext: contextAnalysis.timeContext,
            riskAssessment: contextAnalysis.riskAssessment
          },
          availableKeywords: this.keywordMatcher.getAvailableKeywords()
        }
      });
      return;

    } catch (error) {
      console.error('Error in getKeywordRecommendationsOnly:', error);
      return res.status(500).json({
        success: false,
        error: '키워드 추천 중 오류가 발생했습니다.'
      });
    }
  }

  /**
   * 키워드 병합 (중복 제거, 카테고리별 최고 신뢰도 선택)
   */
  private mergeKeywords(
    textKeywords: KeywordMatch[], 
    contextKeywords: KeywordMatch[]
  ): KeywordMatch[] {
    const allKeywords = [...textKeywords, ...contextKeywords];
    const categoryMap = new Map<string, KeywordMatch>();

    allKeywords.forEach(keyword => {
      const existing = categoryMap.get(keyword.category);
      if (!existing || keyword.confidence > existing.confidence) {
        categoryMap.set(keyword.category, keyword);
      }
    });

    return Array.from(categoryMap.values())
      .sort((a, b) => b.confidence - a.confidence);
  }

  // 헬퍼 메소드들
  private getScoreLevel(totalScore: number): string {
    if (totalScore >= 60) return '안전';
    if (totalScore >= 20) return '보통';
    if (totalScore >= -20) return '주의';
    return '위험';
  }

  private getRecommendations(scoreResult: any): string[] {
    const recommendations: string[] = [];
    
    if (scoreResult.cptedScores.naturalSurveillance < 0) {
      recommendations.push('조명 개선이 필요합니다.');
    }
    if (scoreResult.cptedScores.accessControl < 0) {
      recommendations.push('접근 통제 시설 보완이 필요합니다.');
    }
    if (scoreResult.cptedScores.territoriality < 0) {
      recommendations.push('영역성 표시를 명확히 해야 합니다.');
    }
    if (scoreResult.cptedScores.maintenance < 0) {
      recommendations.push('환경 정리 및 관리가 필요합니다.');
    }
    if (scoreResult.cptedScores.activitySupport < 0) {
      recommendations.push('활동 활성화 방안이 필요합니다.');
    }

    return recommendations.length > 0 ? recommendations : ['현재 안전 상태가 양호합니다.'];
  }
}