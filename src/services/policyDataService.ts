import { promises as fs } from 'fs';
import path from 'path';
import { PolicyModel, CreatePolicyData } from '../models/policy';
import pool from '../config/database';

interface PolicyDataFile {
  policies: CreatePolicyData[];
}

export class PolicyDataService {
  private static readonly DATA_PATH = path.join(__dirname, '../../data/policy-data.json');

  static async loadPolicyData(): Promise<void> {
    try {
      // 정책 데이터 JSON 파일 읽기
      const policyDataContent = await fs.readFile(this.DATA_PATH, 'utf8');
      const policyData: PolicyDataFile = JSON.parse(policyDataContent);

      // 기존 정책 데이터 확인 (중복 방지)
      const existingPolicies = await PolicyModel.findAll();
      const existingTitles = new Set(existingPolicies.map(p => p.title));

      let insertedCount = 0;
      let skippedCount = 0;

      // 각 정책 데이터를 데이터베이스에 삽입
      for (const policyInfo of policyData.policies) {
        if (existingTitles.has(policyInfo.title)) {
          skippedCount++;
          continue;
        }

        try {
          await PolicyModel.create(policyInfo);
          insertedCount++;
        } catch (error) {
          console.error(`❌ Failed to insert policy "${policyInfo.title}":`, error);
        }
      }

      console.log(`📋 Policy data: ${insertedCount} inserted, ${skippedCount} skipped, ${existingPolicies.length + insertedCount} total`);

    } catch (error) {
      console.error('❌ Failed to load policy data:', (error as Error).message);
      throw error;
    }
  }

  static async checkDatabaseConnection(): Promise<boolean> {
    try {
      await pool.query('SELECT 1');
      return true;
    } catch (error) {
      console.error('❌ Database connection failed:', (error as Error).message);
      return false;
    }
  }

  static async ensurePolicyTable(): Promise<void> {
    try {
      // policies 테이블이 존재하는지 확인
      const tableExistsQuery = `
        SELECT EXISTS (
          SELECT FROM information_schema.tables 
          WHERE table_schema = 'public' 
          AND table_name = 'policies'
        );
      `;
      
      const result = await pool.query(tableExistsQuery);
      const tableExists = result.rows[0].exists;
      
      if (!tableExists) {
        console.log('⚠️  Policies table does not exist. Please run the database migration scripts first.');
        throw new Error('Policies table not found');
      }
      
    } catch (error) {
      console.error('❌ Failed to check policies table:', (error as Error).message);
      throw error;
    }
  }
}