import { v4 as uuidv4 } from 'uuid';
import pool from '../config/database';

export interface Participant {
  id: string;
  post_id: string;
  participant_name: string;
  joined_at: Date;
}

export interface JoinMeetupData {
  post_id: string;
  participant_name: string;
}

export class ParticipantModel {
  // Join meetup
  static async join(data: JoinMeetupData): Promise<Participant> {
    const id = uuidv4();
    const now = new Date();
    
    const query = `
      INSERT INTO meetup_participants (id, post_id, participant_name, joined_at)
      VALUES ($1, $2, $3, $4)
      RETURNING *
    `;
    
    const values = [id, data.post_id, data.participant_name, now];
    
    const result = await pool.query(query, values);
    return result.rows[0];
  }

  // Leave meetup
  static async leave(postId: string, participantName: string): Promise<boolean> {
    const query = `
      DELETE FROM meetup_participants 
      WHERE post_id = $1 AND participant_name = $2
    `;
    
    const result = await pool.query(query, [postId, participantName]);
    return (result.rowCount ?? 0) > 0;
  }

  // Get participants by post ID
  static async getByPostId(postId: string): Promise<Participant[]> {
    const query = `
      SELECT * FROM meetup_participants 
      WHERE post_id = $1 
      ORDER BY joined_at ASC
    `;
    
    const result = await pool.query(query, [postId]);
    return result.rows;
  }

  // Check if already joined
  static async isParticipant(postId: string, participantName: string): Promise<boolean> {
    const query = `
      SELECT 1 FROM meetup_participants 
      WHERE post_id = $1 AND participant_name = $2
    `;
    
    const result = await pool.query(query, [postId, participantName]);
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