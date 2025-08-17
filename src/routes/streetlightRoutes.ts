import express, { Request, Response } from 'express';
import { promises as fs } from 'fs';
import path from 'path';
import { StreetLight, StreetLightByDong } from '../types';

const router = express.Router();
const DATA_PATH = path.join(__dirname, '../../data');

let streetLightData: StreetLight[] | null = null;
let safetyData: any = null;

async function loadStreetLightData(): Promise<void> {
  if (streetLightData && safetyData) return;
  
  try {
    const streetLightDataPath = path.join(DATA_PATH, 'streetlight.json');
    const safetyDataPath = path.join(DATA_PATH, 'seoul_map_data.json');
    
    const [streetLightDataContent, safetyDataContent] = await Promise.all([
      fs.readFile(streetLightDataPath, 'utf8'),
      fs.readFile(safetyDataPath, 'utf8')
    ]);
    
    streetLightData = JSON.parse(streetLightDataContent) as StreetLight[];
    safetyData = JSON.parse(safetyDataContent);
    
    console.log(`💡 Streetlight data loaded: ${streetLightData.length} streetlights`);
    console.log(`💡 Safety data loaded: ${safetyData.data.length} dongs`);
  } catch (error) {
    console.error('❌ Failed to load streetlight data:', (error as Error).message);
    throw error;
  }
}

function mapStreetlightDongToSafetyDongs(streetlightDong: string): string[] {
  if (!safetyData) return [];
  
  const safetyDongs = safetyData.data.map((item: any) => item.dong);
  
  // 1. 정확히 일치하는 경우
  if (safetyDongs.includes(streetlightDong)) {
    return [streetlightDong];
  }
  
  // 2. streetlight 동명이 safety 동명에 포함되는 경우 (예: "가양동" -> ["가양1동", "가양2동", "가양3동"])
  const matchingDongs = safetyDongs.filter((dong: string) => {
    // 숫자가 붙은 동명에서 숫자를 제거했을 때 일치하는지 확인
    const baseDong = dong.replace(/[0-9]+동$/, '동');
    return baseDong === streetlightDong;
  });
  
  return matchingDongs;
}

function getAllRelatedStreetlights(dongName: string, allStreetlights: StreetLight[]): StreetLight[] {
  // 요청된 동명과 관련된 모든 streetlight 데이터 수집
  // 예: "영등포동" 요청시 "영등포동1가", "영등포동2가" 등도 포함
  const relatedLights = allStreetlights.filter((light: StreetLight) => {
    const lightDong = light.dong;
    if (!lightDong) return false;
    // 정확히 일치하거나, 요청된 동명으로 시작하는 경우
    return lightDong === dongName || lightDong.startsWith(dongName);
  });
  
  return relatedLights;
}

function getLimitedStreetlights(dongName: string, streetlights: StreetLight[]): StreetLight[] {
  if (!safetyData) return streetlights;
  
  // 매핑된 동명들 가져오기
  const mappedDongs = mapStreetlightDongToSafetyDongs(dongName);
  
  if (mappedDongs.length === 0) {
    console.warn(`⚠️  No safety data found for dong: ${dongName}`);
    return streetlights;
  }
  
  // 매핑된 모든 동의 가로등 개수 합계 계산
  const totalSafetyLimit = mappedDongs.reduce((sum, mappedDong) => {
    const dongSafetyData = safetyData.data.find((item: any) => item.dong === mappedDong);
    return sum + (dongSafetyData?.facilities?.streetlight || 0);
  }, 0);
  
  console.log(`💡 ${dongName} mapped to ${mappedDongs.length} dongs: ${mappedDongs.join(', ')} (total limit: ${totalSafetyLimit})`);
  
  return streetlights.slice(0, totalSafetyLimit);
}

// 동별 가로등 조회
router.get('/dong/:dongName', async (req: Request, res: Response) => {
  try {
    await loadStreetLightData();
    
    if (!streetLightData) {
      return res.status(503).json({ error: 'Streetlight data not loaded' });
    }
    
    const dongName = req.params.dongName;
    // 관련된 모든 streetlight 데이터 수집 (예: "영등포동" -> "영등포동", "영등포동1가", "영등포동2가" 등)
    const allStreetlights = getAllRelatedStreetlights(dongName, streetLightData);
    
    if (allStreetlights.length === 0) {
      return res.status(404).json({ error: 'No streetlights found for this dong' });
    }
    
    // safety API 개수에 맞춰서 제한
    const limitedStreetlights = getLimitedStreetlights(dongName, allStreetlights);
    
    const result: StreetLightByDong = {
      dong: dongName,
      district: allStreetlights[0].district,
      count: limitedStreetlights.length,
      streetlights: limitedStreetlights
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
    const dongGroups = streetlights.reduce((groups: Record<string, StreetLight[]>, light: StreetLight) => {
      if (!groups[light.dong]) {
        groups[light.dong] = [];
      }
      groups[light.dong].push(light);
      return groups;
    }, {});
    
    const dongResults: StreetLightByDong[] = Object.entries(dongGroups).map(([dong, lights]) => {
      // safety API 개수에 맞춰서 제한
      const limitedLights = getLimitedStreetlights(dong, lights as StreetLight[]);
      return {
        dong,
        district: districtName,
        count: limitedLights.length,
        streetlights: limitedLights
      };
    });
    
    const totalLimitedCount = dongResults.reduce((sum, dongResult) => sum + dongResult.count, 0);
    
    return res.json({
      district: districtName,
      total_count: totalLimitedCount,
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
    
    if (!streetLightData || !safetyData) {
      return res.status(503).json({ error: 'Streetlight data not loaded' });
    }
    
    // 동별로 그룹화하고 safety API 제한 적용
    const dongGroups = streetLightData.reduce((groups: Record<string, StreetLight[]>, light: StreetLight) => {
      if (!groups[light.dong]) {
        groups[light.dong] = [];
      }
      groups[light.dong].push(light);
      return groups;
    }, {});
    
    const limitedStreetlights: StreetLight[] = [];
    Object.entries(dongGroups).forEach(([dong, lights]) => {
      const limitedLights = getLimitedStreetlights(dong, lights as StreetLight[]);
      limitedStreetlights.push(...limitedLights);
    });
    
    return res.json({
      total_count: limitedStreetlights.length,
      data: limitedStreetlights
    });
  } catch (error) {
    console.error('Error fetching all streetlight data:', error);
    return res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;