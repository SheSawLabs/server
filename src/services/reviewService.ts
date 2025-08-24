import { Review, ReviewStats } from '../models/review';
import pool from '../config/database';
import { v4 as uuidv4 } from 'uuid';

export class ReviewService {
  
  // 리뷰 생성
  static async createReview(reviewData: Omit<Review, 'id' | 'createdAt' | 'updatedAt'>): Promise<Review> {
    const id = uuidv4();
    const now = new Date();
    
    const query = `
      INSERT INTO reviews (
        id, user_id, review_text, location, time_of_day, rating, 
        selected_keywords, recommended_keywords, score_result, 
        context_analysis, analysis_method, created_at, updated_at
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
      RETURNING *
    `;
    
    const values = [
      id,
      reviewData.user_id || null,
      reviewData.reviewText,
      reviewData.location,
      reviewData.timeOfDay,
      reviewData.rating,
      JSON.stringify(reviewData.selectedKeywords),
      JSON.stringify(reviewData.recommendedKeywords || []),
      JSON.stringify(reviewData.scoreResult || {}),
      JSON.stringify(reviewData.contextAnalysis || {}),
      reviewData.analysisMethod,
      now,
      now
    ];
    
    try {
      const result = await pool.query(query, values);
      return this.mapDbRowToReview(result.rows[0]);
    } catch (error) {
      console.error('Error creating review:', error);
      throw new Error('리뷰 생성 중 오류가 발생했습니다.');
    }
  }
  
  // 리뷰 조회 (ID로)
  static async getReviewById(id: string): Promise<Review | null> {
    const query = `
      SELECT r.*, u.nickname as user_nickname 
      FROM reviews r
      LEFT JOIN users u ON r.user_id = u.id
      WHERE r.id = $1
    `;
    
    try {
      const result = await pool.query(query, [id]);
      return result.rows.length > 0 ? this.mapDbRowToReview(result.rows[0]) : null;
    } catch (error) {
      console.error('Error fetching review:', error);
      throw new Error('리뷰 조회 중 오류가 발생했습니다.');
    }
  }
  
  // 무한 스크롤용 리뷰 목록 조회
  static async getReviews(
    limit: number = 20, 
    cursor?: string,
    filters?: {
      location?: string;
      analysisMethod?: string;
      safetyLevel?: string;
    }
  ): Promise<{ 
    reviews: Review[]; 
    nextCursor: string | null; 
    hasMore: boolean; 
  }> {
    
    let whereConditions = [];
    let queryParams: any[] = [];
    let paramIndex = 1;
    
    // cursor 조건 (created_at 기준으로 이후 데이터만)
    if (cursor) {
      whereConditions.push(`r.created_at < $${paramIndex}`);
      queryParams.push(new Date(cursor));
      paramIndex++;
    }
    
    // 필터 조건들
    if (filters?.location) {
      whereConditions.push(`r.location ILIKE $${paramIndex}`);
      queryParams.push(`%${filters.location}%`);
      paramIndex++;
    }
    
    if (filters?.analysisMethod) {
      whereConditions.push(`r.analysis_method = $${paramIndex}`);
      queryParams.push(filters.analysisMethod);
      paramIndex++;
    }
    
    // 안전도 레벨 필터링 (JSON 필드에서)
    if (filters?.safetyLevel) {
      whereConditions.push(`r.score_result->>'safetyLevel' = $${paramIndex}`);
      queryParams.push(filters.safetyLevel);
      paramIndex++;
    }
    
    const whereClause = whereConditions.length > 0 ? `WHERE ${whereConditions.join(' AND ')}` : '';
    
    // 데이터 조회 (limit + 1개를 가져와서 hasMore 판단)
    const dataQuery = `
      SELECT r.*, u.nickname as user_nickname 
      FROM reviews r
      LEFT JOIN users u ON r.user_id = u.id
      ${whereClause}
      ORDER BY r.created_at DESC 
      LIMIT $${paramIndex}
    `;
    
    queryParams.push(limit + 1); // hasMore 판단용으로 1개 더
    
    try {
      const result = await pool.query(dataQuery, queryParams);
      
      const hasMore = result.rows.length > limit;
      const reviews = result.rows.slice(0, limit).map(row => this.mapDbRowToReview(row));
      
      // 다음 커서는 마지막 아이템의 created_at
      const nextCursor = hasMore && reviews.length > 0 && reviews[reviews.length - 1].createdAt
        ? reviews[reviews.length - 1].createdAt!.toISOString()
        : null;
      
      return {
        reviews,
        nextCursor,
        hasMore
      };
    } catch (error) {
      console.error('Error fetching reviews:', error);
      throw new Error('리뷰 목록 조회 중 오류가 발생했습니다.');
    }
  }
  
  // 리뷰 수정
  static async updateReview(id: string, updateData: Partial<Omit<Review, 'id' | 'createdAt'>>): Promise<Review | null> {
    const now = new Date();
    
    const setFields = [];
    const values = [];
    let paramIndex = 1;
    
    if (updateData.user_id !== undefined) {
      setFields.push(`user_id = $${paramIndex}`);
      values.push(updateData.user_id);
      paramIndex++;
    }
    
    if (updateData.reviewText !== undefined) {
      setFields.push(`review_text = $${paramIndex}`);
      values.push(updateData.reviewText);
      paramIndex++;
    }
    
    if (updateData.location !== undefined) {
      setFields.push(`location = $${paramIndex}`);
      values.push(updateData.location);
      paramIndex++;
    }
    
    if (updateData.timeOfDay !== undefined) {
      setFields.push(`time_of_day = $${paramIndex}`);
      values.push(updateData.timeOfDay);
      paramIndex++;
    }
    
    if (updateData.rating !== undefined) {
      setFields.push(`rating = $${paramIndex}`);
      values.push(updateData.rating);
      paramIndex++;
    }
    
    if (updateData.selectedKeywords !== undefined) {
      setFields.push(`selected_keywords = $${paramIndex}`);
      values.push(JSON.stringify(updateData.selectedKeywords));
      paramIndex++;
    }
    
    if (setFields.length === 0) {
      throw new Error('수정할 데이터가 없습니다.');
    }
    
    setFields.push(`updated_at = $${paramIndex}`);
    values.push(now);
    paramIndex++;
    
    values.push(id);
    
    const query = `
      UPDATE reviews 
      SET ${setFields.join(', ')}
      WHERE id = $${paramIndex}
      RETURNING *
    `;
    
    try {
      const result = await pool.query(query, values);
      return result.rows.length > 0 ? this.mapDbRowToReview(result.rows[0]) : null;
    } catch (error) {
      console.error('Error updating review:', error);
      throw new Error('리뷰 수정 중 오류가 발생했습니다.');
    }
  }
  
  // 리뷰 삭제
  static async deleteReview(id: string): Promise<boolean> {
    const query = 'DELETE FROM reviews WHERE id = $1 RETURNING id';
    
    try {
      const result = await pool.query(query, [id]);
      return result.rows.length > 0;
    } catch (error) {
      console.error('Error deleting review:', error);
      throw new Error('리뷰 삭제 중 오류가 발생했습니다.');
    }
  }
  
  // 통계 정보 조회
  static async getReviewStats(): Promise<ReviewStats> {
    try {
      // 총 리뷰 수
      const totalQuery = 'SELECT COUNT(*) as total FROM reviews';
      const totalResult = await pool.query(totalQuery);
      const totalReviews = parseInt(totalResult.rows[0].total);
      
      // 키워드 사용 통계
      const keywordQuery = `
        SELECT 
          jsonb_array_elements(selected_keywords)->>'keyword' as keyword,
          jsonb_array_elements(selected_keywords)->>'category' as category
        FROM reviews
      `;
      const keywordResult = await pool.query(keywordQuery);
      
      const keywordUsage: { [key: string]: number } = {};
      const categoryUsage: { [key: string]: number } = {};
      
      keywordResult.rows.forEach(row => {
        const keyword = row.keyword;
        const category = row.category;
        
        if (keyword) keywordUsage[keyword] = (keywordUsage[keyword] || 0) + 1;
        if (category) categoryUsage[category] = (categoryUsage[category] || 0) + 1;
      });
      
      // 평균 점수
      const avgScoreQuery = `
        SELECT AVG(CAST(score_result->>'totalScore' AS NUMERIC)) as avg_score
        FROM reviews 
        WHERE score_result->>'totalScore' IS NOT NULL AND score_result->>'totalScore' != ''
      `;
      const avgScoreResult = await pool.query(avgScoreQuery);
      const averageScore = parseFloat(avgScoreResult.rows[0].avg_score) || 0;
      
      // 안전도 레벨 분포
      const safetyLevelQuery = `
        SELECT 
          score_result->>'safetyLevel' as safety_level,
          COUNT(*) as count
        FROM reviews 
        WHERE score_result->>'safetyLevel' IS NOT NULL AND score_result->>'safetyLevel' != ''
        GROUP BY score_result->>'safetyLevel'
      `;
      const safetyLevelResult = await pool.query(safetyLevelQuery);
      
      const safetyLevelDistribution: { [key: string]: number } = {};
      safetyLevelResult.rows.forEach(row => {
        safetyLevelDistribution[row.safety_level] = parseInt(row.count);
      });
      
      // 분석 방법 분포
      const analysisMethodQuery = `
        SELECT 
          analysis_method,
          COUNT(*) as count
        FROM reviews 
        GROUP BY analysis_method
      `;
      const analysisMethodResult = await pool.query(analysisMethodQuery);
      
      const analysisMethodDistribution: { [key: string]: number } = {};
      analysisMethodResult.rows.forEach(row => {
        analysisMethodDistribution[row.analysis_method] = parseInt(row.count);
      });

      // 키워드 선택 통계 (각 키워드가 몇 명의 사용자에 의해 선택되었는지)
      const keywordSelectionStats = await this.getKeywordSelectionStats();

      return {
        totalReviews,
        keywordUsage,
        categoryUsage,
        averageScore,
        safetyLevelDistribution,
        analysisMethodDistribution,
        keywordSelectionStats
      };
    } catch (error) {
      console.error('Error getting review stats:', error);
      throw new Error('통계 조회 중 오류가 발생했습니다.');
    }
  }

  // 동별 통계 조회
  static async getLocationStats(location: string): Promise<{
    location: string;
    averageRating: number;
    totalReviews: number;
    topKeywords: { keyword: string; count: number; percentage: number }[];
  }> {
    try {
      // 해당 동의 리뷰들 조회
      const reviewQuery = `
        SELECT rating, selected_keywords 
        FROM reviews 
        WHERE location ILIKE $1
      `;
      const reviewResult = await pool.query(reviewQuery, [`%${location}%`]);
      
      const totalReviews = reviewResult.rows.length;
      if (totalReviews === 0) {
        return {
          location,
          averageRating: 0,
          totalReviews: 0,
          topKeywords: []
        };
      }

      // 평균 rating 계산
      const ratings = reviewResult.rows.map(row => row.rating).filter(r => r !== null);
      const averageRating = ratings.length > 0 
        ? Math.round((ratings.reduce((sum, r) => sum + r, 0) / ratings.length) * 10) / 10 
        : 0;

      // 키워드 통계 계산
      const keywordCounts: { [key: string]: number } = {};
      reviewResult.rows.forEach(row => {
        const selectedKeywords = row.selected_keywords || [];
        selectedKeywords.forEach((item: any) => {
          if (item.keyword) {
            keywordCounts[item.keyword] = (keywordCounts[item.keyword] || 0) + 1;
          }
        });
      });

      // 상위 키워드 3개 선택
      const topKeywords = Object.entries(keywordCounts)
        .map(([keyword, count]) => ({
          keyword,
          count,
          percentage: Math.round((count / totalReviews) * 100)
        }))
        .sort((a, b) => b.count - a.count)
        .slice(0, 3);

      return {
        location,
        averageRating,
        totalReviews,
        topKeywords
      };
    } catch (error) {
      console.error('Error getting location stats:', error);
      throw new Error('동별 통계 조회 중 오류가 발생했습니다.');
    }
  }

  // 키워드 선택 통계 (몇 명이 각 키워드를 선택했는지)
  static async getKeywordSelectionStats(): Promise<{
    totalUsers: number;
    keywordSelections: { [keyword: string]: { count: number; percentage: number } };
    categorySelections: { [category: string]: { count: number; percentage: number } };
  }> {
    try {
      // 총 사용자 수 (리뷰 작성자 수)
      const totalUsersQuery = 'SELECT COUNT(*) as total FROM reviews';
      const totalUsersResult = await pool.query(totalUsersQuery);
      const totalUsers = parseInt(totalUsersResult.rows[0].total);

      // 각 키워드를 선택한 사용자 수
      const keywordSelectionQuery = `
        SELECT 
          jsonb_array_elements(selected_keywords)->>'keyword' as keyword,
          jsonb_array_elements(selected_keywords)->>'category' as category,
          COUNT(DISTINCT id) as user_count
        FROM reviews
        WHERE jsonb_array_length(selected_keywords) > 0
        GROUP BY 
          jsonb_array_elements(selected_keywords)->>'keyword',
          jsonb_array_elements(selected_keywords)->>'category'
        ORDER BY user_count DESC
      `;
      const keywordSelectionResult = await pool.query(keywordSelectionQuery);

      const keywordSelections: { [keyword: string]: { count: number; percentage: number } } = {};
      const categorySelections: { [category: string]: { count: number; percentage: number } } = {};

      keywordSelectionResult.rows.forEach(row => {
        const keyword = row.keyword;
        const category = row.category;
        const count = parseInt(row.user_count);
        const percentage = totalUsers > 0 ? Math.round((count / totalUsers) * 100) : 0;

        if (keyword) {
          keywordSelections[keyword] = { count, percentage };
        }
        
        if (category) {
          if (!categorySelections[category]) {
            categorySelections[category] = { count: 0, percentage: 0 };
          }
          categorySelections[category].count += count;
        }
      });

      // 카테고리별 백분율 재계산
      Object.keys(categorySelections).forEach(category => {
        const count = categorySelections[category].count;
        categorySelections[category].percentage = totalUsers > 0 ? Math.round((count / totalUsers) * 100) : 0;
      });

      return {
        totalUsers,
        keywordSelections,
        categorySelections
      };
    } catch (error) {
      console.error('Error getting keyword selection stats:', error);
      throw new Error('키워드 선택 통계 조회 중 오류가 발생했습니다.');
    }
  }
  
  // DB 행을 Review 객체로 매핑
  private static mapDbRowToReview(row: any): Review {
    return {
      id: row.id,
      user_id: row.user_id,
      reviewText: row.review_text,
      location: row.location,
      timeOfDay: row.time_of_day,
      rating: row.rating,
      selectedKeywords: row.selected_keywords || [],
      recommendedKeywords: row.recommended_keywords || [],
      scoreResult: row.score_result || {},
      contextAnalysis: row.context_analysis || {},
      analysisMethod: row.analysis_method,
      createdAt: new Date(row.created_at),
      updatedAt: new Date(row.updated_at),
      nickname: row.user_nickname || null  // 추가: 사용자 닉네임
    };
  }
}