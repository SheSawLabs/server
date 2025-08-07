import { v4 as uuidv4 } from 'uuid';
import pool from '../config/database';

export interface Meetup {
  id: string;
  title: string;
  content: string;
  image_url?: string;
  location: string;
  date: Date;
  created_at: Date;
  updated_at: Date;
}

export interface CreateMeetupData {
  title: string;
  content: string;
  image_url?: string;
  location: string;
  date: Date;
}

export class MeetupModel {
  static async create(data: CreateMeetupData): Promise<Meetup> {
    const id = uuidv4();
    const now = new Date();
    
    const query = `
      INSERT INTO meetups (id, title, content, image_url, location, date, created_at, updated_at)
      VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
      RETURNING *
    `;
    
    const values = [
      id,
      data.title,
      data.content,
      data.image_url,
      data.location,
      data.date,
      now,
      now
    ];
    
    const result = await pool.query(query, values);
    return result.rows[0];
  }

  static async findById(id: string): Promise<Meetup | null> {
    const query = 'SELECT * FROM meetups WHERE id = $1';
    const result = await pool.query(query, [id]);
    return result.rows[0] || null;
  }

  static async findAll(): Promise<Meetup[]> {
    const query = 'SELECT * FROM meetups ORDER BY date DESC';
    const result = await pool.query(query);
    return result.rows;
  }
}