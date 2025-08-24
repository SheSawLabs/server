## mock 데이터 생성 스크립트 실행 방법

### 방법 1: npm 스크립트로 실행

```bash
# user 목데이터, review 목데이터 생성
npm run mock
```

### 방법 2: psql 명령줄에서 직접 실행

```bash
# PostgreSQL에 접속하여 .env 에 있는 설정값으로 스크립트 실행
source .env && PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f scripts/create-mock-reviews.sql
```
