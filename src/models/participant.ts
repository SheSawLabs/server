import { v4 as uuidv4 } from 'uuid';
import pool from '../config/database';

export interface Participant {
  id: string;
  post_id: string;
  user_id: number;
  joined_at: Date;
}

export interface JoinMeetupData {
  post_id: string;
  user_id: number;
}

export class ParticipantModel {
  // Join meetup
  static async join(data: JoinMeetupData): Promise<Participant> {
    const id = uuidv4();
    const now = new Date();
    
    const query = `
      INSERT INTO meetup_participants (id, post_id, user_id, joined_at)
      VALUES ($1, $2, $3, $4)
      RETURNING *
    `;
    
    const values = [id, data.post_id, data.user_id, now];
    
    const result = await pool.query(query, values);
    return result.rows[0];
  }

  // Leave meetup
  static async leave(postId: string, userId: string): Promise<boolean> {
    const query = `
      DELETE FROM meetup_participants 
      WHERE post_id = $1 AND user_id = $2
    `;
    
    const result = await pool.query(query, [postId, parseInt(userId)]);
    return (result.rowCount ?? 0) > 0;
  }

  // Get participants by post ID
  static async getByPostId(postId: string): Promise<Participant[]> {
    const query = `
      SELECT mp.*, u.nickname, u.profile_image 
      FROM meetup_participants mp
      LEFT JOIN users u ON mp.user_id = u.id
      WHERE mp.post_id = $1 
      ORDER BY mp.joined_at ASC
    `;
    
    const result = await pool.query(query, [postId]);
    console.log('🔍 [PARTICIPANT MODEL] SQL 결과:', result.rows);
    return result.rows;
  }

  // Check if already joined
  static async isParticipant(postId: string, userId: string): Promise<boolean> {
    const query = `
      SELECT 1 FROM meetup_participants 
      WHERE post_id = $1 AND user_id = $2
    `;
    
    const result = await pool.query(query, [postId, parseInt(userId)]);
    return result.rows.length > 0;
  }

  // Get participant count
  static async getParticipantCount(postId: string): Promise<number> {
    const query = `
      SELECT COUNT(*) as count FROM meetup_participants 
      WHERE post_id = $1
    `;
    
    const result = await pool.query(query, [postId]);
    return parseInt(result.rows[0].count);
  }
}