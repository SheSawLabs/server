# Seoul Safety API Server

서울시 안전도 데이터를 제공하는 Express.js API 서버입니다.

## 파일 구조

```
src/
├── app.ts          # 메인 애플리케이션 서버
├── types.ts        # TypeScript 타입 정의
├── config/         # 데이터베이스 설정
├── controllers/    # API 컨트롤러
├── models/         # 데이터 모델
├── routes/         # API 라우트 정의
└── middleware/     # 미들웨어
```

## 주요 기능

### Safety API Endpoints

- `GET /api/safety/map` - 전체 지도 데이터 (50개 동)
- `GET /api/safety/report` - 상세 리포트 데이터
- `GET /api/safety/dong/:dongCode` - 특정 동 데이터
- `GET /api/safety/district/:district` - 구별 데이터
- `GET /api/safety/grade/:grade` - 안전등급별 데이터 (A, B, C, D, E)

### 기본 Endpoints

- `GET /` - 서버 정보
- `GET /health` - 헬스 체크
- `GET /api/posts/*` - 게시물 관련 API

## 데이터 구조

### DongData (동 데이터)

```typescript
interface DongData {
  dong_code: string; // 동 코드
  district: string; // 구 이름
  dong: string; // 동 이름
  grade: "A" | "B" | "C" | "D" | "E"; // 안전등급
  score: number; // 안전점수
  coordinates: Coordinates; // 좌표 (위도, 경도)
  facilities: Facilities; // 시설 정보
  risk_factors: RiskFactors; // 위험 요소
}
```

### Facilities (시설 정보)

```typescript
interface Facilities {
  cctv: number; // CCTV 개수
  streetlight: number; // 가로등 개수
  police_station: number; // 경찰서 개수
  safety_house: number; // 안심집 개수
  delivery_box: number; // 택배보관함 개수
}
```

## 데이터 로딩

서버 시작 시 `data/` 폴더에서 JSON 파일을 자동으로 로드합니다:

- `map_data.json` - 지도 데이터
- `report_data.json` - 리포트 데이터

## 실행 방법

```bash
# 개발 서버 실행
npm run dev

# 프로덕션 빌드
npm run build

# 프로덕션 실행
npm start
```

## API 사용 예시

### 전체 지도 데이터 조회

```bash
curl http://localhost:3001/api/safety/map
```

### 특정 동 데이터 조회

```bash
curl http://localhost:3001/api/safety/dong/80171
```

### 구별 데이터 조회

```bash
curl "http://localhost:3001/api/safety/district/강동구"
```

### 안전등급별 조회

```bash
curl http://localhost:3001/api/safety/grade/A
```
