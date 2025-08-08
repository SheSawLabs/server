import { v4 as uuidv4 } from 'uuid';
import pool from '../config/database';

export interface Like {
  id: string;
  post_id: string;
  user_name: string;
  created_at: Date;
}

export interface CreateLikeData {
  post_id: string;
  user_name: string;
}

export class LikeModel {
  // Add like (toggle functionality)
  static async toggle(data: CreateLikeData): Promise<{ liked: boolean; likeCount: number }> {
    // Check if already liked
    const existingLike = await this.findByPostAndUser(data.post_id, data.user_name);
    
    if (existingLike) {
      // Unlike - remove existing like
      await this.remove(data.post_id, data.user_name);
      const likeCount = await this.getCountByPostId(data.post_id);
      return { liked: false, likeCount };
    } else {
      // Like - add new like
      const id = uuidv4();
      const now = new Date();
      
      const query = `
        INSERT INTO likes (id, post_id, user_name, created_at)
        VALUES ($1, $2, $3, $4)
        RETURNING *
      `;
      
      await pool.query(query, [id, data.post_id, data.user_name, now]);
      const likeCount = await this.getCountByPostId(data.post_id);
      return { liked: true, likeCount };
    }
  }

  // Remove like
  static async remove(postId: string, userName: string): Promise<boolean> {
    const query = `
      DELETE FROM likes 
      WHERE post_id = $1 AND user_name = $2
    `;
    
    const result = await pool.query(query, [postId, userName]);
    return (result.rowCount ?? 0) > 0;
  }

  // Find like by post and user
  static async findByPostAndUser(postId: string, userName: string): Promise<Like | null> {
    const query = `
      SELECT * FROM likes 
      WHERE post_id = $1 AND user_name = $2
    `;
    
    const result = await pool.query(query, [postId, userName]);
    return result.rows[0] || null;
  }

  // Get like count by post ID
  static async getCountByPostId(postId: string): Promise<number> {
    const query = `
      SELECT COUNT(*) as count FROM likes 
      WHERE post_id = $1
    `;
    
    const result = await pool.query(query, [postId]);
    return parseInt(result.rows[0].count);
  }

  // Get likes by post ID (for admin purposes)
  static async getByPostId(postId: string): Promise<Like[]> {
    const query = `
      SELECT * FROM likes 
      WHERE post_id = $1 
      ORDER BY created_at DESC
    `;
    
    const result = await pool.query(query, [postId]);
    return result.rows;
  }

  // Check if user liked the post
  static async isLikedByUser(postId: string, userName: string): Promise<boolean> {
    const like = await this.findByPostAndUser(postId, userName);
    return like !== null;
  }
}