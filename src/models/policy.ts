import { v4 as uuidv4 } from 'uuid';
import pool from '../config/database';

export interface TargetConditions {
  income?: string[];
  family_type?: string[];
  location?: string[];
  age?: string[];
  employment?: string[];
}

export interface Policy {
  id: string;
  title: string;
  description: string;
  application_period?: string;
  eligibility_criteria?: string;
  link?: string;
  category?: string;
  target_conditions?: TargetConditions;
  created_at: Date;
  updated_at: Date;
}

export interface CreatePolicyData {
  title: string;
  description: string;
  application_period?: string;
  eligibility_criteria?: string;
  link?: string;
  category?: string;
  target_conditions?: TargetConditions;
}

export class PolicyModel {
  static async findAll(): Promise<Policy[]> {
    const query = 'SELECT * FROM policies ORDER BY created_at DESC';
    const result = await pool.query(query);
    return result.rows.map(policy => ({
      ...policy,
      target_conditions: policy.target_conditions && typeof policy.target_conditions === 'string' 
        ? JSON.parse(policy.target_conditions) 
        : policy.target_conditions
    }));
  }

  static async findById(id: string): Promise<Policy | null> {
    const query = 'SELECT * FROM policies WHERE id = $1';
    const result = await pool.query(query, [id]);
    const policy = result.rows[0];
    if (!policy) return null;
    
    return {
      ...policy,
      target_conditions: policy.target_conditions && typeof policy.target_conditions === 'string' 
        ? JSON.parse(policy.target_conditions) 
        : policy.target_conditions
    };
  }

  static async findByCategory(category: string): Promise<Policy[]> {
    const query = 'SELECT * FROM policies WHERE category = $1 ORDER BY created_at DESC';
    const result = await pool.query(query, [category]);
    return result.rows.map(policy => ({
      ...policy,
      target_conditions: policy.target_conditions && typeof policy.target_conditions === 'string' 
        ? JSON.parse(policy.target_conditions) 
        : policy.target_conditions
    }));
  }

  static async create(data: CreatePolicyData): Promise<Policy> {
    const id = uuidv4();
    const now = new Date();
    
    const query = `
      INSERT INTO policies (id, title, description, application_period, eligibility_criteria, link, category, target_conditions, created_at, updated_at)
      VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
      RETURNING *
    `;
    
    const values = [
      id,
      data.title,
      data.description,
      data.application_period,
      data.eligibility_criteria,
      data.link,
      data.category,
      data.target_conditions ? JSON.stringify(data.target_conditions) : null,
      now,
      now
    ];
    
    const result = await pool.query(query, values);
    const policy = result.rows[0];
    
    // target_conditions를 JSON으로 파싱 (이미 객체인 경우 스킵)
    if (policy.target_conditions && typeof policy.target_conditions === 'string') {
      policy.target_conditions = JSON.parse(policy.target_conditions);
    }
    
    return policy;
  }

  static async deleteAll(): Promise<number> {
    const query = 'DELETE FROM policies';
    const result = await pool.query(query);
    return result.rowCount || 0;
  }
}