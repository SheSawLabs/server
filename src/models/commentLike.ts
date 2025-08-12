import { v4 as uuidv4 } from 'uuid';
import pool from '../config/database';

export interface CommentLike {
  id: string;
  comment_id: string;
  user_id: number;
  created_at: Date;
}

export interface CreateCommentLikeData {
  comment_id: string;
  user_id: number;
}

export class CommentLikeModel {
  // Add like (toggle functionality)
  static async toggle(data: CreateCommentLikeData): Promise<{ liked: boolean; likeCount: number }> {
    // Check if already liked
    const existingLike = await this.findByCommentAndUser(data.comment_id, data.user_id);
    
    if (existingLike) {
      // Unlike - remove existing like
      await this.remove(data.comment_id, data.user_id);
      const likeCount = await this.getCountByCommentId(data.comment_id);
      return { liked: false, likeCount };
    } else {
      // Like - add new like
      const id = uuidv4();
      const now = new Date();
      
      const query = `
        INSERT INTO comment_likes (id, comment_id, user_id, created_at)
        VALUES ($1, $2, $3, $4)
        RETURNING *
      `;
      
      await pool.query(query, [id, data.comment_id, data.user_id, now]);
      const likeCount = await this.getCountByCommentId(data.comment_id);
      return { liked: true, likeCount };
    }
  }

  // Remove like
  static async remove(commentId: string, userId: number): Promise<boolean> {
    const query = `
      DELETE FROM comment_likes 
      WHERE comment_id = $1 AND user_id = $2
    `;
    
    const result = await pool.query(query, [commentId, userId]);
    return (result.rowCount ?? 0) > 0;
  }

  // Find like by comment and user
  static async findByCommentAndUser(commentId: string, userId: number): Promise<CommentLike | null> {
    const query = `
      SELECT * FROM comment_likes 
      WHERE comment_id = $1 AND user_id = $2
    `;
    
    const result = await pool.query(query, [commentId, userId]);
    return result.rows[0] || null;
  }

  // Get like count by comment ID
  static async getCountByCommentId(commentId: string): Promise<number> {
    const query = `
      SELECT COUNT(*) as count FROM comment_likes 
      WHERE comment_id = $1
    `;
    
    const result = await pool.query(query, [commentId]);
    return parseInt(result.rows[0].count);
  }

  // Get likes by comment ID (for admin purposes)
  static async getByCommentId(commentId: string): Promise<CommentLike[]> {
    const query = `
      SELECT * FROM comment_likes 
      WHERE comment_id = $1 
      ORDER BY created_at DESC
    `;
    
    const result = await pool.query(query, [commentId]);
    return result.rows;
  }

  // Check if user liked the comment
  static async isLikedByUser(commentId: string, userId: number): Promise<boolean> {
    const like = await this.findByCommentAndUser(commentId, userId);
    return like !== null;
  }
}