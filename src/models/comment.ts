import { v4 as uuidv4 } from 'uuid';
import pool from '../config/database';

export interface Comment {
  id: string;
  post_id: string;
  parent_comment_id?: string;
  author_id: number;
  content: string;
  created_at: Date;
  updated_at: Date;
}

export interface CreateCommentData {
  post_id: string;
  parent_comment_id?: string;
  author_id: number;
  content: string;
}

export class CommentModel {
  // Create comment
  static async create(data: CreateCommentData): Promise<Comment> {
    const id = uuidv4();
    const now = new Date();
    
    const query = `
      INSERT INTO comments (id, post_id, parent_comment_id, author_id, content, created_at, updated_at)
      VALUES ($1, $2, $3, $4, $5, $6, $7)
      RETURNING *
    `;
    
    const values = [id, data.post_id, data.parent_comment_id, data.author_id, data.content, now, now];
    
    const result = await pool.query(query, values);
    return result.rows[0];
  }

  // Get comments by post ID
  static async getByPostId(postId: string): Promise<Comment[]> {
    const query = `
      SELECT * FROM comments 
      WHERE post_id = $1 
      ORDER BY created_at ASC
    `;
    
    const result = await pool.query(query, [postId]);
    return result.rows;
  }

  // Delete comment by ID
  static async deleteById(commentId: string, authorId: number): Promise<boolean> {
    const query = `
      DELETE FROM comments 
      WHERE id = $1 AND author_id = $2
    `;
    
    const result = await pool.query(query, [commentId, authorId]);
    return (result.rowCount ?? 0) > 0;
  }

  // Get comment count by post ID
  static async getCountByPostId(postId: string): Promise<number> {
    const query = `
      SELECT COUNT(*) as count FROM comments 
      WHERE post_id = $1
    `;
    
    const result = await pool.query(query, [postId]);
    return parseInt(result.rows[0].count);
  }

  // Check if comment exists
  static async findById(commentId: string): Promise<Comment | null> {
    const query = 'SELECT * FROM comments WHERE id = $1';
    const result = await pool.query(query, [commentId]);
    return result.rows[0] || null;
  }
}