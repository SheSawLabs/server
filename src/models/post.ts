import { v4 as uuidv4 } from 'uuid';
import pool from '../config/database';

export type PostCategory = '수리' | '소분' | '취미' | '기타' | '일반';
export type PostStatus = 'recruiting' | 'active' | 'full';

export interface Post {
  id: string;
  title: string;
  content: string;
  category: PostCategory;
  author_id: number;
  image_url?: string;
  location?: string;
  date?: Date;
  min_participants?: number;
  max_participants?: number;
  status?: PostStatus;
  created_at: Date;
  updated_at: Date;
}

export interface CreatePostData {
  title: string;
  content: string;
  category: PostCategory;
  author_id: number;
  image_url?: string;
  location?: string;
  date?: Date;
  min_participants?: number;
  max_participants?: number;
}

export class PostModel {
  // Create post
  static async create(data: CreatePostData): Promise<Post> {
    const id = uuidv4();
    const now = new Date();
    
    const query = `
      INSERT INTO posts (id, title, content, category, author_id, image_url, location, date, min_participants, max_participants, created_at, updated_at)
      VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
      RETURNING *
    `;
    
    const values = [
      id,
      data.title,
      data.content,
      data.category,
      data.author_id,
      data.image_url,
      data.location,
      data.date,
      data.min_participants,
      data.max_participants,
      now,
      now
    ];
    
    const result = await pool.query(query, values);
    return result.rows[0];
  }

  // Find by ID
  static async findById(id: string, incrementView: boolean = false): Promise<Post | null> {
    // 조회수 증가
    if (incrementView) {
      await pool.query('UPDATE posts SET views = views + 1 WHERE id = $1', [id]);
    }
    
    const query = `
      SELECT p.*,
             u.nickname as author_nickname,
             u.profile_image as author_profile_image
      FROM posts p
      LEFT JOIN users u ON p.author_id = u.id
      WHERE p.id = $1
    `;
    const result = await pool.query(query, [id]);
    return result.rows[0] || null;
  }

  // Find all by category with stats
  static async findByCategory(category: PostCategory): Promise<Post[]> {
    const query = `
      SELECT p.*,
             COALESCE(like_count.count, 0) as likes_count,
             COALESCE(comment_count.count, 0) as comments_count,
             COALESCE(p.views, 0) as views_count
      FROM posts p
      LEFT JOIN (
        SELECT post_id, COUNT(*) as count 
        FROM likes 
        GROUP BY post_id
      ) like_count ON p.id = like_count.post_id
      LEFT JOIN (
        SELECT post_id, COUNT(*) as count 
        FROM comments 
        GROUP BY post_id
      ) comment_count ON p.id = comment_count.post_id
      WHERE p.category = $1 
      ORDER BY p.created_at DESC
    `;
    const result = await pool.query(query, [category]);
    return result.rows;
  }

  // Find all posts with stats and user like status
  static async findAll(category?: PostCategory, userId?: string): Promise<Post[]> {
    const userLikeSubquery = userId 
      ? `SELECT post_id, user_id FROM likes WHERE user_id = ${parseInt(userId)}`
      : `SELECT post_id, user_id FROM likes WHERE 1=0`;
    
    let query = `
      SELECT p.*,
             COALESCE(like_count.count, 0) as likes_count,
             COALESCE(comment_count.count, 0) as comments_count,
             COALESCE(p.views, 0) as views_count,
             CASE WHEN user_likes.user_id IS NOT NULL THEN 'true' ELSE 'false' END as is_liked,
             u.nickname as author_nickname,
             u.profile_image as author_profile_image
      FROM posts p
      LEFT JOIN users u ON p.author_id = u.id
      LEFT JOIN (
        SELECT post_id, COUNT(*) as count 
        FROM likes 
        GROUP BY post_id
      ) like_count ON p.id = like_count.post_id
      LEFT JOIN (
        SELECT post_id, COUNT(*) as count 
        FROM comments 
        GROUP BY post_id
      ) comment_count ON p.id = comment_count.post_id
      LEFT JOIN (
        ${userLikeSubquery}
      ) user_likes ON p.id = user_likes.post_id
    `;
    const values: any[] = [];
    
    if (category) {
      query += ' WHERE p.category = $1';
      values.push(category);
    }
    
    query += ' ORDER BY p.created_at DESC';
    
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

  // Update meetup status based on participant count
  static async updateMeetupStatus(postId: string): Promise<void> {
    const query = `
      UPDATE posts 
      SET status = CASE 
        WHEN (SELECT COUNT(*) FROM meetup_participants WHERE post_id = $1) >= max_participants THEN 'full'
        WHEN (SELECT COUNT(*) FROM meetup_participants WHERE post_id = $1) >= min_participants THEN 'active'
        ELSE 'recruiting'
      END,
      updated_at = NOW()
      WHERE id = $1 AND category != '일반'
    `;
    
    await pool.query(query, [postId]);
  }

  // Get meetup with participant info
  static async findMeetupWithParticipants(postId: string): Promise<Post & { current_participants: number } | null> {
    const query = `
      SELECT p.*, 
             COALESCE(participant_count.count, 0) as current_participants
      FROM posts p
      LEFT JOIN (
        SELECT post_id, COUNT(*) as count 
        FROM meetup_participants 
        WHERE post_id = $1 
        GROUP BY post_id
      ) participant_count ON p.id = participant_count.post_id
      WHERE p.id = $1
    `;
    
    const result = await pool.query(query, [postId]);
    return result.rows[0] || null;
  }
}