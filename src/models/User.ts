import { pool } from '../config/database';
import { User, KakaoUserInfo } from '../types';

export class UserModel {
  /**
   * 카카오 사용자 찾기 또는 생성
   */
  static async findOrCreateKakaoUser(kakaoUser: KakaoUserInfo): Promise<User> {
    const client = await pool.connect();
    
    try {
      await client.query('BEGIN');
      
      // 기존 사용자 찾기
      const findQuery = `
        SELECT * FROM users 
        WHERE provider = 'kakao' AND provider_id = $1
      `;
      
      const existingUser = await client.query(findQuery, [kakaoUser.id]);
      
      if (existingUser.rows.length > 0) {
        // 기존 사용자 - 마지막 로그인 시간과 프로필 업데이트
        const updateQuery = `
          UPDATE users 
          SET last_login_at = CURRENT_TIMESTAMP,
              nickname = COALESCE($2, nickname),
              profile_image = COALESCE($3, profile_image),
              thumbnail_image = COALESCE($4, thumbnail_image)
          WHERE id = $1
          RETURNING *
        `;
        
        const result = await client.query(updateQuery, [
          existingUser.rows[0].id,
          kakaoUser.nickname || kakaoUser.properties?.nickname,
          kakaoUser.profileImage || kakaoUser.properties?.profile_image,
          kakaoUser.thumbnailImage || kakaoUser.properties?.thumbnail_image
        ]);
        
        await client.query('COMMIT');
        return UserModel.mapDbRowToUser(result.rows[0]);
      } else {
        // 새 사용자 생성 (카카오는 nickname, profile_image, thumbnail_image만)
        const insertQuery = `
          INSERT INTO users (
            provider, provider_id, nickname, 
            profile_image, thumbnail_image
          ) VALUES ($1, $2, $3, $4, $5)
          RETURNING *
        `;
        
        const result = await client.query(insertQuery, [
          'kakao',
          kakaoUser.id,
          kakaoUser.nickname || kakaoUser.properties?.nickname,
          kakaoUser.profileImage || kakaoUser.properties?.profile_image,
          kakaoUser.thumbnailImage || kakaoUser.properties?.thumbnail_image
        ]);
        
        await client.query('COMMIT');
        return UserModel.mapDbRowToUser(result.rows[0]);
      }
    } catch (error) {
      await client.query('ROLLBACK');
      console.error('카카오 사용자 생성/업데이트 실패:', error);
      throw new Error('사용자 정보 처리에 실패했습니다.');
    } finally {
      client.release();
    }
  }
  
  /**
   * ID로 사용자 찾기
   */
  static async findById(id: number): Promise<User | null> {
    try {
      const query = 'SELECT * FROM users WHERE id = $1';
      const result = await pool.query(query, [id]);
      
      if (result.rows.length === 0) {
        return null;
      }
      
      return UserModel.mapDbRowToUser(result.rows[0]);
    } catch (error) {
      console.error('사용자 조회 실패:', error);
      throw new Error('사용자 조회에 실패했습니다.');
    }
  }
  
  /**
   * 제공자와 제공자 ID로 사용자 찾기
   */
  static async findByProviderAndId(provider: 'kakao' | 'naver', providerId: string): Promise<User | null> {
    try {
      const query = 'SELECT * FROM users WHERE provider = $1 AND provider_id = $2';
      const result = await pool.query(query, [provider, providerId]);
      
      if (result.rows.length === 0) {
        return null;
      }
      
      return UserModel.mapDbRowToUser(result.rows[0]);
    } catch (error) {
      console.error('사용자 조회 실패:', error);
      throw new Error('사용자 조회에 실패했습니다.');
    }
  }
  
  /**
   * DB 행을 User 객체로 변환
   */
  private static mapDbRowToUser(row: any): User {
    return {
      id: row.id,
      kakao_id: row.provider_id,
      email: row.email || '',
      nickname: row.nickname,
      profile_image: row.profile_image,
      created_at: new Date(row.created_at),
      updated_at: new Date(row.updated_at),
      provider: row.provider,
      providerId: row.provider_id
    };
  }
}