import pool from '../config/database';

export interface NotificationKeyword {
  id: number;
  user_id: number;
  keyword: string;
  created_at: Date;
}

export class NotificationKeywordModel {
  // 키워드 추가
  static async createKeyword(userId: number, keyword: string): Promise<NotificationKeyword> {
    const query = `
      INSERT INTO notification_keywords (user_id, keyword)
      VALUES ($1, $2)
      RETURNING *
    `;
    
    const result = await pool.query(query, [userId, keyword]);
    return result.rows[0];
  }

  // 사용자별 키워드 목록 조회
  static async getKeywordsByUserId(userId: number): Promise<NotificationKeyword[]> {
    const query = `
      SELECT * FROM notification_keywords
      WHERE user_id = $1
      ORDER BY created_at DESC
    `;
    
    const result = await pool.query(query, [userId]);
    return result.rows;
  }

  // 키워드 삭제
  static async deleteKeyword(userId: number, keyword: string): Promise<boolean> {
    const query = `
      DELETE FROM notification_keywords
      WHERE user_id = $1 AND keyword = $2
    `;
    
    const result = await pool.query(query, [userId, keyword]);
    return (result.rowCount ?? 0) > 0;
  }

  // 키워드 중복 확인
  static async checkKeywordExists(userId: number, keyword: string): Promise<boolean> {
    const query = `
      SELECT 1 FROM notification_keywords
      WHERE user_id = $1 AND keyword = $2
    `;
    
    const result = await pool.query(query, [userId, keyword]);
    return (result.rowCount ?? 0) > 0;
  }
}