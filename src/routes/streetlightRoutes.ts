import express, { Request, Response } from 'express';
import { promises as fs } from 'fs';
import path from 'path';
import { StreetLight, StreetLightByDong } from '../types';

const router = express.Router();
const DATA_PATH = path.join(__dirname, '../../data');

let streetLightData: StreetLight[] | null = null;

async function loadStreetLightData(): Promise<void> {
  if (streetLightData) return;
  
  try {
    const streetLightDataPath = path.join(DATA_PATH, 'streetlight.json');
    const streetLightDataContent = await fs.readFile(streetLightDataPath, 'utf8');
    streetLightData = JSON.parse(streetLightDataContent) as StreetLight[];
    console.log(`💡 Streetlight data loaded: ${streetLightData.length} streetlights`);
  } catch (error) {
    console.error('❌ Failed to load streetlight data:', (error as Error).message);
    throw error;
  }
}

// 동별 가로등 조회
router.get('/dong/:dongName', async (req: Request, res: Response) => {
  try {
    await loadStreetLightData();
    
    if (!streetLightData) {
      return res.status(503).json({ error: 'Streetlight data not loaded' });
    }
    
    const dongName = req.params.dongName;
    const streetlights = streetLightData.filter((light: StreetLight) => light.dong === dongName);
    
    if (streetlights.length === 0) {
      return res.status(404).json({ error: 'No streetlights found for this dong' });
    }
    
    const result: StreetLightByDong = {
      dong: dongName,
      district: streetlights[0].district,
      count: streetlights.length,
      streetlights: streetlights
    };
    
    return res.json(result);
  } catch (error) {
    console.error('Error fetching streetlight data by dong:', error);
    return res.status(500).json({ error: 'Internal server error' });
  }
});

// 구별 가로등 조회 (동별로 그룹화)
router.get('/district/:districtName', async (req: Request, res: Response) => {
  try {
    await loadStreetLightData();
    
    if (!streetLightData) {
      return res.status(503).json({ error: 'Streetlight data not loaded' });
    }
    
    const districtName = req.params.districtName;
    const streetlights = streetLightData.filter((light: StreetLight) => light.district === districtName);
    
    if (streetlights.length === 0) {
      return res.status(404).json({ error: 'No streetlights found for this district' });
    }
    
    // 동별로 그룹화
    const dongGroups = streetlights.reduce((groups: Record<string, StreetLight[]>, light) => {
      if (!groups[light.dong]) {
        groups[light.dong] = [];
      }
      groups[light.dong].push(light);
      return groups;
    }, {});
    
    const dongResults: StreetLightByDong[] = Object.entries(dongGroups).map(([dong, lights]) => ({
      dong,
      district: districtName,
      count: lights.length,
      streetlights: lights
    }));
    
    return res.json({
      district: districtName,
      total_count: streetlights.length,
      dong_count: dongResults.length,
      data: dongResults
    });
  } catch (error) {
    console.error('Error fetching streetlight data by district:', error);
    return res.status(500).json({ error: 'Internal server error' });
  }
});

// 전체 가로등 조회
router.get('/all', async (req: Request, res: Response) => {
  try {
    await loadStreetLightData();
    
    if (!streetLightData) {
      return res.status(503).json({ error: 'Streetlight data not loaded' });
    }
    
    return res.json({
      total_count: streetLightData.length,
      data: streetLightData
    });
  } catch (error) {
    console.error('Error fetching all streetlight data:', error);
    return res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;