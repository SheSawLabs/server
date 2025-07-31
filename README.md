# Seoul Safety Data Pipeline 🏙️🔒

> **서울시 안전 데이터 수집 및 관리 파이프라인**  
> 다양한 공공 API로부터 서울시 안전 관련 데이터를 수집하고 통합 관리하는 시스템

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue.svg)](https://postgresql.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-blue.svg)](https://docker.com)

## 🎯 프로젝트 개요

서울시의 안전 관련 시설 정보를 공공 API로부터 자동으로 수집하고, 지오코딩을 통해 위치 정보를 보강하여 통합 데이터베이스에 저장하는 파이프라인입니다.

### 📊 수집 대상 데이터

| 데이터 유형 | 설명 | 현재 상태 |
|------------|------|-----------|
| 🚔 **경찰서/지구대/파출소** | 서울시 경찰 시설 243개소 | ✅ 완료 |
| 💡 **가로등** | 서울시 가로등 설치 현황 | ✅ 완료 |
| 🏠 **여성안심지킴이집** | 여성 안전 보호 시설 | ✅ 완료 |
| ⚠️ **성범죄자 거주지** | 공개된 성범죄자 주소 정보 | ✅ 완료 |
| 📹 **CCTV** | 서울시 CCTV 설치 현황 | ✅ 완료 |
| 📦 **안심택배함** | 안전한 택배 수령 시설 | ✅ 완료 |

## 🏗️ 시스템 아키텍처

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   공공 API      │────│  Data Pipeline  │────│   PostgreSQL    │
│                 │    │                 │    │                 │
│ • 서울 열린데이터│    │ • 컨트롤러       │    │ • 통합 저장      │
│ • 공공데이터포털 │    │ • 스케줄러       │    │ • 지오코딩 보강   │
│ • ODCloud API   │    │ • 지오코딩       │    │ • 인덱싱 최적화   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚀 주요 기능

### 1. 데이터 수집 컨트롤러
- **자동화된 API 호출**: 각 데이터 소스별 전용 컨트롤러
- **에러 처리**: 재시도 로직 및 예외 상황 대응
- **배치 처리**: 대용량 데이터 효율적 처리
- **중복 제거**: UPSERT 방식으로 데이터 무결성 보장

### 2. 지오코딩 시스템
- **주소 → 좌표 변환**: Kakao Local API 활용
- **좌표 → 주소 변환**: 역지오코딩 지원
- **주소 파싱**: 구/동 정보 자동 추출
- **좌표 검증**: 대한민국 영역 내 좌표 확인

### 3. 스케줄러
- **자동 수집**: 정기적인 데이터 업데이트
- **API 제한 관리**: 일일 호출 한도 준수
- **로깅**: 상세한 실행 로그 및 통계

## 📁 프로젝트 구조

```
seoul-safety-data-pipeline/
├── controllers/                 # 데이터 수집 컨트롤러
│   ├── streetlight_controller.py
│   ├── police_station_controller.py
│   ├── female_safety_house_controller.py
│   ├── sexual_offender_controller.py
│   ├── cctv_controller.py
│   └── delivery_box_controller.py
├── scheduler/                   # 스케줄링 시스템
│   ├── streetlight_scheduler.py
│   └── sexual_offender_scheduler.py
├── utils/                      # 유틸리티 모듈
│   ├── api_utils.py
│   ├── geocoding.py
│   ├── address_parser.py
│   ├── data_go_kr_api.py
│   └── odcloud_api.py
├── scripts/                    # 스크립트 모음
│   ├── geocoding.py
│   ├── parse_csv.py
│   └── assign_dong.py
├── db/                        # 데이터베이스 관련
│   ├── db_connection.py
│   ├── init_schema.py
│   └── schemas/               # SQL 스키마 정의
├── config/                    # 설정 파일
│   └── settings.py
├── docker-compose.yml         # Docker 구성
├── Dockerfile
└── requirements.txt
```

## 🛠️ 설치 및 실행

### 1. 환경 설정

```bash
# 저장소 클론
git clone https://github.com/SheSawLabs/server.git
cd server

# 환경변수 설정
cp .env.example .env
# .env 파일에 API 키 설정 필요
```

### 2. Docker로 실행 (권장)

```bash
# 데이터베이스 및 애플리케이션 실행
docker compose up -d

# 개발 환경 실행
docker compose --profile dev up -d dev
```

### 3. 로컬 실행

```bash
# 의존성 설치
pip install -r requirements.txt

# PostgreSQL 데이터베이스 준비 후
python main.py
```

## 🔑 API 키 설정

`.env` 파일에 다음 API 키들을 설정해야 합니다:

```env
# 카카오 로컬 API (지오코딩)
KAKAO_API_KEY=your_kakao_api_key

# 서울 열린데이터광장
SEOUL_OPEN_API_KEY=your_seoul_open_api_key

# 공공데이터포털 API 키들
SEXUAL_OFFENDER_API_KEY=your_sexual_offender_api_key
SEOUL_STREETLIGHT_API_KEY=your_streetlight_api_key
WOMEN_SAFETY_API_KEY=your_women_safety_api_key
```

## 📊 데이터베이스 스키마

각 안전 시설별로 최적화된 테이블 구조:

- `police_stations` - 경찰서/지구대/파출소 정보
- `streetlight_installations` - 가로등 설치 현황
- `female_safety_houses` - 여성안심지킴이집
- `sexual_offender_addresses` - 성범죄자 거주지 정보
- `cctv_installations` - CCTV 설치 현황
- `safe_delivery_boxes` - 안심택배함 위치

## 🎯 사용 예시

### 개별 컨트롤러 실행
```bash
# 경찰서 데이터 수집
docker exec shesaw_dev python3 controllers/police_station_controller.py

# 가로등 데이터 수집
docker exec shesaw_dev python3 controllers/streetlight_controller.py
```

### 스케줄러 실행
```bash
# 정기 수집 스케줄러 실행
docker exec shesaw_dev python3 scheduler/streetlight_scheduler.py
```

## 📈 성과

- **✅ 완료된 데이터 수집**
  - 서울시 경찰서 243개소 수집 완료
  - 가로등 설치 현황 데이터 수집 완료
  - 여성안심지킴이집 데이터 수집 완료
  - 성범죄자 거주지 정보 수집 완료

- **🔧 기술적 성과**
  - 안정적인 API 연동 시스템 구축
  - 효율적인 지오코딩 파이프라인 구현
  - Docker 기반 컨테이너화 완료
  - 확장 가능한 아키텍처 설계

## 🚀 향후 계획

- [ ] 실시간 데이터 수집 시스템
- [ ] Web Dashboard 개발
- [ ] 데이터 분석 및 시각화
- [ ] API 서버 구축
- [ ] 모바일 앱 연동

## 🤝 기여하기

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 라이선스

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👥 개발팀

- **SheSaw Labs** - *Initial work* - [SheSawLabs](https://github.com/SheSawLabs)
- **Claude (Anthropic)** - *AI Assistant & Code Collaboration*

---

> 💡 **이 프로젝트는 Claude AI와의 협업으로 개발되었습니다.**  
> 인공지능과 인간의 협력으로 만들어진 실용적인 공공 데이터 파이프라인입니다.