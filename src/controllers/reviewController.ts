import { Request, Response } from 'express';
import { AIService } from '../services/aiService';
import { ScoreCalculator, SelectedKeyword } from '../services/scoreCalculator';
import { GPTPromptService } from '../services/gptPromptService';
import { PublicDataService } from '../services/publicDataService';
import { ReviewService } from '../services/reviewService';

export class ReviewController {
  private aiService: AIService;

  constructor() {
    this.aiService = new AIService();
  }

  // GPT 키워드 추천 API
  async getKeywordRecommendations(req: Request, res: Response) {
    try {
      const { reviewText } = req.body;

      if (!reviewText || typeof reviewText !== 'string') {
        return res.status(400).json({
          success: false,
          error: '리뷰 텍스트가 필요합니다.'
        });
      }

      if (reviewText.length > 1000) {
        return res.status(400).json({
          success: false,
          error: '리뷰 텍스트는 1000자 이하여야 합니다.'
        });
      }

      const analysis = await this.aiService.analyzeReview(reviewText);

      res.json({
        success: true,
        data: {
          recommendedKeywords: analysis.recommendedKeywords,
          emotionalSummary: analysis.emotionalSummary,
          situationSummary: analysis.situationSummary,
          availableKeywords: GPTPromptService.getAvailableKeywords()
        }
      });

    } catch (error) {
      console.error('Error in getKeywordRecommendations:', error);
      res.status(500).json({
        success: false,
        error: '키워드 추천 중 오류가 발생했습니다.'
      });
    }
  }

  // 점수 계산 API
  async calculateScore(req: Request, res: Response) {
    try {
      const { selectedKeywords, reviewText } = req.body;

      if (!selectedKeywords || !Array.isArray(selectedKeywords)) {
        return res.status(400).json({
          success: false,
          error: '선택된 키워드 목록이 필요합니다.'
        });
      }

      // 키워드 유효성 검증
      const availableKeywords = GPTPromptService.getAvailableKeywords();
      const validKeywords: SelectedKeyword[] = selectedKeywords.filter(item => {
        const categoryKeywords = availableKeywords[item.category as keyof typeof availableKeywords];
        return categoryKeywords && (categoryKeywords as readonly string[]).includes(item.keyword);
      });

      if (validKeywords.length === 0) {
        return res.status(400).json({
          success: false,
          error: '유효한 키워드가 없습니다.'
        });
      }

      const scoreResult = ScoreCalculator.calculateScore(validKeywords);

      res.json({
        success: true,
        data: {
          reviewText: reviewText || '',
          selectedKeywords: validKeywords,
          scoreResult
        }
      });

    } catch (error) {
      console.error('Error in calculateScore:', error);
      res.status(500).json({
        success: false,
        error: '점수 계산 중 오류가 발생했습니다.'
      });
    }
  }

  // 키워드와 별점 기반 분석 API (줄글 선택적)
  async analyzeWithKeywordsAndRating(req: Request, res: Response) {
    try {
      const { selectedKeywords, rating, reviewText, location, timeOfDay } = req.body;

      // 필수: 키워드와 별점
      if (!selectedKeywords || !Array.isArray(selectedKeywords) || selectedKeywords.length === 0) {
        return res.status(400).json({
          success: false,
          error: '선택된 키워드가 필요합니다.'
        });
      }

      if (rating === undefined || rating === null || rating < 1 || rating > 5) {
        return res.status(400).json({
          success: false,
          error: '1-5 사이의 별점이 필요합니다.'
        });
      }

      // 키워드 유효성 검증
      const availableKeywords = GPTPromptService.getAvailableKeywords();
      const validKeywords: SelectedKeyword[] = selectedKeywords.filter(item => {
        const categoryKeywords = availableKeywords[item.category as keyof typeof availableKeywords];
        return categoryKeywords && (categoryKeywords as readonly string[]).includes(item.keyword);
      });

      if (validKeywords.length === 0) {
        return res.status(400).json({
          success: false,
          error: '유효한 키워드가 없습니다.'
        });
      }

      // 점수 계산 (키워드 + 별점)
      const scoreResult = ScoreCalculator.calculateScore(validKeywords, rating);

      // 선택적: 텍스트 분석 (줄글이 있는 경우)
      let gptAnalysis = null;
      if (reviewText && typeof reviewText === 'string' && reviewText.trim().length > 0) {
        if (reviewText.length <= 1000) {
          gptAnalysis = await this.aiService.analyzeReview(reviewText, location, timeOfDay);
        }
      }

      // 공공데이터 정보 조회
      let publicData = null;
      if (location) {
        const safetyData = PublicDataService.findByLocation(location);
        if (safetyData) {
          publicData = {
            location: `${safetyData.district} ${safetyData.dong}`,
            grade: safetyData.grade,
            score: safetyData.score,
            facilities: safetyData.facilities,
            riskFactors: safetyData.risk_factors,
            recommendedKeywords: PublicDataService.getKeywordRecommendationsByData(safetyData)
          };
        }
      }

      res.json({
        success: true,
        data: {
          selectedKeywords: validKeywords,
          rating,
          reviewText: reviewText || '',
          location: location || '',
          timeOfDay: timeOfDay || '',
          scoreResult,
          gptAnalysis,
          publicData,
          availableKeywords
        }
      });

    } catch (error) {
      console.error('Error in analyzeWithKeywordsAndRating:', error);
      res.status(500).json({
        success: false,
        error: '분석 중 오류가 발생했습니다.'
      });
    }
  }

  // 통합 분석 API (추천 + 점수계산) - DB 저장 포함
  async analyzeReviewComplete(req: Request, res: Response) {
    try {
      const { reviewText, selectedKeywords, location, timeOfDay, rating } = req.body;

      if (!reviewText || typeof reviewText !== 'string') {
        return res.status(400).json({
          success: false,
          error: '리뷰 텍스트가 필요합니다.'
        });
      }

      // 1. GPT 키워드 추천
      const gptAnalysis = await this.aiService.analyzeReview(reviewText);

      // 2. 점수 계산 (키워드가 선택된 경우)
      let scoreResult = null;
      let finalKeywords: SelectedKeyword[] = [];
      
      if (selectedKeywords && Array.isArray(selectedKeywords) && selectedKeywords.length > 0) {
        const availableKeywords = GPTPromptService.getAvailableKeywords();
        finalKeywords = selectedKeywords.filter(item => {
          const categoryKeywords = availableKeywords[item.category as keyof typeof availableKeywords];
          return categoryKeywords && (categoryKeywords as readonly string[]).includes(item.keyword);
        });

        if (finalKeywords.length > 0) {
          scoreResult = ScoreCalculator.calculateScore(finalKeywords);
        }
      }

      // 3. 리뷰 저장
      try {
        const savedReview = await ReviewService.createReview({
          reviewText,
          location,
          timeOfDay,
          rating,
          selectedKeywords: finalKeywords,
          recommendedKeywords: gptAnalysis.recommendedKeywords,
          scoreResult: scoreResult ? {
            totalScore: scoreResult.totalScore,
            categoryScores: Object.entries(scoreResult.categoryScores).reduce((acc, [key, value]) => {
              acc[key] = (value as any).score;
              return acc;
            }, {} as { [key: string]: number }),
            safetyLevel: this.getScoreLevel(scoreResult.totalScore),
            recommendations: this.getRecommendations(scoreResult)
          } : undefined,
          contextAnalysis: {
            emotionalSummary: gptAnalysis.emotionalSummary,
            situationSummary: gptAnalysis.situationSummary
          },
          analysisMethod: 'gpt'
        });

        res.json({
          success: true,
          data: {
            reviewId: savedReview.id,
            reviewText,
            gptAnalysis: {
              recommendedKeywords: gptAnalysis.recommendedKeywords,
              emotionalSummary: gptAnalysis.emotionalSummary,
              situationSummary: gptAnalysis.situationSummary
            },
            scoreResult,
            availableKeywords: GPTPromptService.getAvailableKeywords()
          }
        });
      } catch (dbError) {
        // DB 저장 실패해도 분석 결과는 반환
        console.error('DB 저장 실패:', dbError);
        res.json({
          success: true,
          data: {
            reviewText,
            gptAnalysis: {
              recommendedKeywords: gptAnalysis.recommendedKeywords,
              emotionalSummary: gptAnalysis.emotionalSummary,
              situationSummary: gptAnalysis.situationSummary
            },
            scoreResult,
            availableKeywords: GPTPromptService.getAvailableKeywords(),
            warning: 'DB 저장에 실패했지만 분석은 완료되었습니다.'
          }
        });
      }

    } catch (error) {
      console.error('Error in analyzeReviewComplete:', error);
      res.status(500).json({
        success: false,
        error: '리뷰 분석 중 오류가 발생했습니다.'
      });
    }
  }

  // 사용 가능한 키워드 목록 API
  async getAvailableKeywords(req: Request, res: Response) {
    try {
      const availableKeywords = GPTPromptService.getAvailableKeywords();
      const cptedWeights = ScoreCalculator.getCPTEDWeights();
      const keywordMapping = ScoreCalculator.getKeywordMapping();

      res.json({
        success: true,
        data: {
          availableKeywords,
          cptedWeights,
          keywordMapping
        }
      });

    } catch (error) {
      console.error('Error in getAvailableKeywords:', error);
      res.status(500).json({
        success: false,
        error: '키워드 정보 조회 중 오류가 발생했습니다.'
      });
    }
  }

  // =========================
  // 리뷰 CRUD 기능들
  // =========================

  // 리뷰 목록 조회 (무한 스크롤)
  async getReviews(req: Request, res: Response) {
    try {
      const { 
        limit = '20', 
        cursor, 
        location, 
        analysisMethod, 
        safetyLevel 
      } = req.query;

      const limitNum = parseInt(limit as string);
      if (limitNum > 50) {
        return res.status(400).json({
          success: false,
          error: '한 번에 최대 50개까지만 조회할 수 있습니다.'
        });
      }

      const filters = {
        location: location as string,
        analysisMethod: analysisMethod as string,
        safetyLevel: safetyLevel as string
      };

      // undefined 값들 제거
      Object.keys(filters).forEach(key => {
        if (filters[key as keyof typeof filters] === undefined) {
          delete filters[key as keyof typeof filters];
        }
      });

      const result = await ReviewService.getReviews(
        limitNum, 
        cursor as string, 
        Object.keys(filters).length > 0 ? filters : undefined
      );

      res.json({
        success: true,
        data: result
      });

    } catch (error) {
      console.error('Error in getReviews:', error);
      res.status(500).json({
        success: false,
        error: '리뷰 목록 조회 중 오류가 발생했습니다.'
      });
    }
  }

  // 리뷰 상세 조회
  async getReview(req: Request, res: Response) {
    try {
      const { id } = req.params;

      if (!id) {
        return res.status(400).json({
          success: false,
          error: '리뷰 ID가 필요합니다.'
        });
      }

      const review = await ReviewService.getReviewById(id);

      if (!review) {
        return res.status(404).json({
          success: false,
          error: '리뷰를 찾을 수 없습니다.'
        });
      }

      res.json({
        success: true,
        data: review
      });

    } catch (error) {
      console.error('Error in getReview:', error);
      res.status(500).json({
        success: false,
        error: '리뷰 조회 중 오류가 발생했습니다.'
      });
    }
  }

  // 리뷰 수정
  async updateReview(req: Request, res: Response) {
    try {
      const { id } = req.params;
      const updateData = req.body;

      if (!id) {
        return res.status(400).json({
          success: false,
          error: '리뷰 ID가 필요합니다.'
        });
      }

      const updatedReview = await ReviewService.updateReview(id, updateData);

      if (!updatedReview) {
        return res.status(404).json({
          success: false,
          error: '리뷰를 찾을 수 없습니다.'
        });
      }

      res.json({
        success: true,
        data: updatedReview,
        message: '리뷰가 성공적으로 수정되었습니다.'
      });

    } catch (error) {
      console.error('Error in updateReview:', error);
      res.status(500).json({
        success: false,
        error: '리뷰 수정 중 오류가 발생했습니다.'
      });
    }
  }

  // 리뷰 삭제
  async deleteReview(req: Request, res: Response) {
    try {
      const { id } = req.params;

      if (!id) {
        return res.status(400).json({
          success: false,
          error: '리뷰 ID가 필요합니다.'
        });
      }

      const deleted = await ReviewService.deleteReview(id);

      if (!deleted) {
        return res.status(404).json({
          success: false,
          error: '리뷰를 찾을 수 없습니다.'
        });
      }

      res.json({
        success: true,
        message: '리뷰가 성공적으로 삭제되었습니다.'
      });

    } catch (error) {
      console.error('Error in deleteReview:', error);
      res.status(500).json({
        success: false,
        error: '리뷰 삭제 중 오류가 발생했습니다.'
      });
    }
  }

  // 통계 정보 조회
  async getReviewStats(req: Request, res: Response) {
    try {
      const stats = await ReviewService.getReviewStats();

      res.json({
        success: true,
        data: stats
      });

    } catch (error) {
      console.error('Error in getReviewStats:', error);
      res.status(500).json({
        success: false,
        error: '통계 정보 조회 중 오류가 발생했습니다.'
      });
    }
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