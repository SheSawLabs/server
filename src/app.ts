import express, { Request, Response } from 'express';
import cors from 'cors';
import helmet from 'helmet';
import morgan from 'morgan';
import dotenv from 'dotenv';
import path from 'path';
import { promises as fs } from 'fs';
import postRoutes from './routes/postRoutes';
import reviewRoutes from './routes/reviewRoutes';
import restrictedRoutes from './routes/restrictedRoutes';
import { MapData, ReportData, DongData } from './types';

dotenv.config();

const app = express();
const PORT = process.env.PORT || 3000;

const DATA_PATH = path.join(__dirname, '../data');

let mapData: MapData | null = null;
let reportData: ReportData | null = null;

// Middleware
app.use(helmet());
app.use(cors());
app.use(morgan('combined'));
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true }));

// Static files for uploaded images
app.use('/uploads', express.static(path.join(process.cwd(), 'uploads')));

// Routes
app.get('/', (req: Request, res: Response) => {
  res.json({
    message: 'SheSawLabs Server API',
    version: '1.0.0',
    status: 'running'
  });
});

app.get('/health', (req: Request, res: Response) => {
  res.status(200).json({
    status: 'healthy',
    timestamp: new Date().toISOString()
  });
});

async function loadSafetyData(): Promise<void> {
  try {
    const mapDataPath = path.join(DATA_PATH, 'map_data.json');
    const reportDataPath = path.join(DATA_PATH, 'report_data.json');
    
    const [mapDataContent, reportDataContent] = await Promise.all([
      fs.readFile(mapDataPath, 'utf8'),
      fs.readFile(reportDataPath, 'utf8')
    ]);
    
    mapData = JSON.parse(mapDataContent) as MapData;
    reportData = JSON.parse(reportDataContent) as ReportData;
    
    console.log('✅ Safety data loaded successfully');
    console.log(`📍 Map data: ${mapData.metadata.total_dong} dong`);
    console.log(`📊 Report data loaded`);
  } catch (error) {
    console.error('❌ Failed to load safety data:', (error as Error).message);
  }
}

// API Routes
app.use('/api/posts', postRoutes);
app.use('/api/review', reviewRoutes);
app.use('/api/restricted', restrictedRoutes);

// Safety API Routes
app.get('/api/safety/map', (req: Request, res: Response) => {
  if (!mapData) {
    return res.status(503).json({ error: 'Safety data not loaded' });
  }
  res.json(mapData);
});

app.get('/api/safety/report', (req: Request, res: Response) => {
  if (!reportData) {
    return res.status(503).json({ error: 'Safety data not loaded' });
  }
  res.json(reportData);
});

app.get('/api/safety/dong/:dongCode', (req: Request, res: Response) => {
  if (!mapData) {
    return res.status(503).json({ error: 'Safety data not loaded' });
  }
  
  const dongCode = req.params.dongCode;
  const dong = mapData.data.find((d: DongData) => d.dong_code === dongCode);
  
  if (!dong) {
    return res.status(404).json({ error: 'Dong not found' });
  }
  
  res.json(dong);
});

app.get('/api/safety/district/:district', (req: Request, res: Response) => {
  if (!mapData) {
    return res.status(503).json({ error: 'Safety data not loaded' });
  }
  
  const district = req.params.district;
  const dongs = mapData.data.filter((d: DongData) => d.district === district);
  
  if (dongs.length === 0) {
    return res.status(404).json({ error: 'District not found' });
  }
  
  res.json({
    district,
    count: dongs.length,
    data: dongs
  });
});

app.get('/api/safety/grade/:grade', (req: Request, res: Response) => {
  if (!mapData) {
    return res.status(503).json({ error: 'Safety data not loaded' });
  }
  
  const grade = req.params.grade.toUpperCase() as 'A' | 'B' | 'C' | 'D' | 'E';
  const dongs = mapData.data.filter((d: DongData) => d.grade === grade);
  
  res.json({
    grade,
    count: dongs.length,
    data: dongs
  });
});

// 404 handler
app.use('*', (req: Request, res: Response) => {
  res.status(404).json({
    error: 'Route not found',
    path: req.originalUrl
  });
});

// Error handler
app.use((err: Error, req: Request, res: Response) => {
  console.error(err.stack);
  res.status(500).json({
    error: 'Internal server error',
    message: process.env.NODE_ENV === 'development' ? err.message : 'Something went wrong'
  });
});

async function startServer(): Promise<void> {
  await loadSafetyData();
  
  app.listen(PORT, () => {
    console.log(`🚀 Server running on port ${PORT}`);
    console.log(`📍 Environment: ${process.env.NODE_ENV || 'development'}`);
    console.log(`📡 Available safety endpoints:`);
    console.log(`   GET /api/safety/map - Full map data`);
    console.log(`   GET /api/safety/report - Detailed report`);
    console.log(`   GET /api/safety/dong/:dongCode - Specific dong data`);
    console.log(`   GET /api/safety/district/:district - District data`);
    console.log(`   GET /api/safety/grade/:grade - Filter by safety grade`);
  });
}

startServer().catch(console.error);

export default app;