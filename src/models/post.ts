import { v4 as uuidv4 } from 'uuid';
import pool from '../config/database';

export type PostCategory = '수리' | '소분' | '취미' | '기타' | '일반';

export interface Post {
  id: string;
  title: string;
  content: string;
  category: PostCategory;
  image_url?: string;
  location?: string;
  date?: Date;
  created_at: Date;
  updated_at: Date;
}

export interface CreatePostData {
  title: string;
  content: string;
  category: PostCategory;
  image_url?: string;
  location?: string;
  date?: Date;
}

export class PostModel {
  // Create post
  static async create(data: CreatePostData): Promise<Post> {
    const id = uuidv4();
    const now = new Date();
    
    const query = `
      INSERT INTO posts (id, title, content, category, image_url, location, date, created_at, updated_at)
      VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
      RETURNING *
    `;
    
    const values = [
      id,
      data.title,
      data.content,
      data.category,
      data.image_url,
      data.location,
      data.date,
      now,
      now
    ];
    
    const result = await pool.query(query, values);
    return result.rows[0];
  }

  // Find by ID
  static async findById(id: string): Promise<Post | null> {
    const query = 'SELECT * FROM posts WHERE id = $1';
    const result = await pool.query(query, [id]);
    return result.rows[0] || null;
  }

  // Find all by category
  static async findByCategory(category: PostCategory): Promise<Post[]> {
    const query = 'SELECT * FROM posts WHERE category = $1 ORDER BY created_at DESC';
    const result = await pool.query(query, [category]);
    return result.rows;
  }

  // Find all posts (with optional category filter)
  static async findAll(category?: PostCategory): Promise<Post[]> {
    let query = 'SELECT * FROM posts';
    const values: any[] = [];
    
    if (category) {
      query += ' WHERE category = $1';
      values.push(category);
    }
    
    query += ' ORDER BY created_at DESC';
    
    const result = await pool.query(query, values);
    return result.rows;
  }

  // Find meetups (all categories except '일반')
  static async findMeetups(): Promise<Post[]> {
    const query = 'SELECT * FROM posts WHERE category != $1 ORDER BY created_at DESC';
    const result = await pool.query(query, ['일반']);
    return result.rows;
  }

  // Find general posts (category = '일반')
  static async findGeneralPosts(): Promise<Post[]> {
    return this.findByCategory('일반');
  }
}