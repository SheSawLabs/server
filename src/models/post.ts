import { v4 as uuidv4 } from 'uuid';
import pool from '../config/database';

export interface Post {
  id: string;
  title: string;
  content: string;
  created_at: Date;
  updated_at: Date;
}

export interface CreatePostData {
  title: string;
  content: string;
}

export class PostModel {
  static async create(data: CreatePostData): Promise<Post> {
    const id = uuidv4();
    const now = new Date();
    
    const query = `
      INSERT INTO posts (id, title, content, created_at, updated_at)
      VALUES ($1, $2, $3, $4, $5)
      RETURNING *
    `;
    
    const values = [
      id,
      data.title,
      data.content,
      now,
      now
    ];
    
    const result = await pool.query(query, values);
    return result.rows[0];
  }

  static async findById(id: string): Promise<Post | null> {
    const query = 'SELECT * FROM posts WHERE id = $1';
    const result = await pool.query(query, [id]);
    return result.rows[0] || null;
  }

  static async findAll(): Promise<Post[]> {
    const query = 'SELECT * FROM posts ORDER BY created_at DESC';
    const result = await pool.query(query);
    return result.rows;
  }
}