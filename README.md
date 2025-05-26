# 🏢 회사 재무정보 검색 시스템

한국의 모든 법인 정보를 검색하고 **DART Open API를 통한 재무정보 시각화**가 가능한 웹 애플리케이션입니다.

## 📋 프로젝트 개요

이 프로젝트는 CORPCODE.xml 파일에서 회사 정보를 추출하여 SQLite 데이터베이스에 저장하고, **금융감독원 DART Open API**를 활용해 상장회사의 재무정보를 시각화하는 시스템입니다.

## 🚀 주요 기능

### 📊 **NEW! 재무정보 시각화**
- **DART Open API 연동**: 실시간 재무데이터 조회
- **인터랙티브 차트**: Chart.js 기반 동적 시각화
- **다양한 분석**: 3년간 추이, 재무비율, 구성분석
- **4가지 탭 구성**: 재무개요/추이분석/재무비율/재무제표

### 🔍 **기존 기능**
- **회사 정보 파싱**: CORPCODE.xml 파일에서 112,476개의 회사 정보 추출
- **데이터베이스 저장**: SQLite 데이터베이스에 효율적으로 저장
- **웹 검색 인터페이스**: 직관적이고 현대적인 UI로 회사 검색
- **실시간 검색**: 회사명, 법인코드, 주식코드로 실시간 검색
- **페이지네이션**: 대량의 데이터를 페이지 단위로 효율적 표시
- **반응형 디자인**: 모바일과 데스크톱 모두 지원

## 📁 파일 구조

```
finance2/
├── CORPCODE.xml              # 원본 회사 정보 XML 파일 (27MB)
├── companies.db              # SQLite 데이터베이스 (9.5MB)
├── parse_corpcode.py         # XML 파싱 스크립트
├── check_database.py         # 데이터베이스 확인 스크립트
├── check_database_detailed.py # 상세 데이터베이스 분석
├── app.py                    # Flask 웹 애플리케이션 + DART API 연동
├── templates/
│   ├── index.html           # 메인 웹 페이지
│   └── company_detail.html  # 회사 상세 페이지 (재무정보 시각화)
├── requirements.txt          # Python 의존성
├── README.md                # 프로젝트 설명서
└── DART_API_GUIDE.md        # DART API 키 발급 가이드
```

## 🛠️ 설치 및 실행

### 1. 의존성 설치
```bash
pip install -r requirements.txt
```

### 2. 데이터베이스 생성 (이미 완료됨)
```bash
python parse_corpcode.py
```

### 3. DART API 키 설정 (재무정보 기능 사용시)
**상세 가이드**: [`DART_API_GUIDE.md`](DART_API_GUIDE.md) 참조

```python
# app.py에서 API 키 설정
DART_API_KEY = "발급받은_40자리_API키"
```

### 4. 웹 애플리케이션 실행
```bash
python app.py
```

### 5. 웹 브라우저에서 접속
```
http://localhost:5000
```

## 💾 데이터베이스 구조

### companies 테이블
| 컬럼명 | 데이터타입 | 설명 |
|--------|------------|------|
| id | INTEGER | 기본키 (자동증가) |
| corp_code | TEXT | 법인코드 (고유) |
| corp_name | TEXT | 회사명 |
| corp_name_eng | TEXT | 영문 회사명 |
| stock_code | TEXT | 주식코드 |
| modify_date | TEXT | 수정일 |
| created_at | TIMESTAMP | 생성일시 |

## 🌐 API 엔드포인트

### 기존 API
- **GET /api/companies**: 회사 목록 조회 (페이지네이션 및 검색 지원)
- **GET /api/company/<corp_code>**: 특정 회사 정보 조회
- **GET /api/stats**: 데이터베이스 통계 정보 조회

### 🆕 새로운 재무정보 API
- **GET /company/<corp_code>**: 회사 상세 페이지 (재무정보 시각화)
- **GET /api/financial/<corp_code>**: 회사 재무정보 API
  - **쿼리 파라미터**:
    - `year`: 사업연도 (기본값: 2023)
    - `report_type`: 보고서 코드 (기본값: 11011-사업보고서)

## 📊 재무정보 시각화 기능

### 📈 **4가지 분석 탭**

#### 1. 재무 개요
- **자산/부채/자본 구성**: 도넛 차트로 재무구조 한눈에 파악
- **수익성 지표**: 영업이익률, 순이익률, ROE 막대차트

#### 2. 추이 분석
- **매출액 추이**: 최근 3년간 매출 성장세 선그래프
- **이익 추이**: 영업이익 vs 순이익 비교 차트

#### 3. 재무 비율
- **수익성**: 영업이익률, 순이익률, ROE, ROA
- **안정성**: 부채비율, 유동비율, 자기자본비율
- **카드 형태**: 직관적인 수치 표시

#### 4. 재무제표
- **주요 계정**: 3년간 재무제표 데이터 테이블
- **비교 분석**: 당기/전기/전전기 수치 비교

### 🎨 **Chart.js 기반 시각화**
- **반응형 차트**: 모든 기기에서 최적화된 표시
- **인터랙티브**: 호버 효과, 범례 클릭 등
- **다양한 차트**: 선형, 막대, 도넛 차트 조합

## 📊 데이터 통계

- **총 등록 회사**: 112,476개
- **상장 회사**: 3,864개 (실제 주식코드 보유)
- **비상장 회사**: 108,612개
- **파일 크기**: 원본 XML (27MB) → 데이터베이스 (9.5MB)
- **압축률**: 약 65% 감소

## 🔧 주요 기술

- **Backend**: Python Flask + DART Open API
- **Database**: SQLite
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla)
- **Data Visualization**: Chart.js
- **XML Parsing**: Python xml.etree.ElementTree
- **HTTP Client**: Python requests
- **Design**: CSS Grid, Flexbox, 반응형 디자인

## 📱 화면 구성

### 메인 페이지
- 통계 정보 대시보드 (상장/비상장 구분)
- 검색 인터페이스
- 회사 목록 (카드 형태, 상장 여부 표시)
- 페이지네이션

### 🆕 회사 상세 페이지
- **헤더**: 회사 기본정보 + 주식코드 배지
- **탭 메뉴**: 4가지 재무분석 탭
- **연도 선택**: 2021-2023년 데이터 조회
- **차트 영역**: 동적 시각화 차트
- **데이터 테이블**: 상세 재무제표

### 주요 UI 특징
- 현대적인 그라디언트 디자인
- 호버 효과와 애니메이션
- 모바일 친화적 반응형 레이아웃
- 직관적인 검색 및 네비게이션
- **상장회사 시각적 구분**: 녹색 배지 및 테두리

## 🚀 향후 개선 계획

### 단기 목표 (1-2개월)
1. **더 많은 재무지표**: PER, PBR, EPS 등 추가
2. **업종별 비교**: 동종업계 평균 대비 분석
3. **재무비율 트렌드**: 비율 변화 추이 차트
4. **데이터 내보내기**: Excel, PDF 다운로드

### 중기 목표 (3-6개월)
1. **실시간 주가 연동**: 증권 API 연계
2. **기업 공시 알림**: 실시간 공시 정보
3. **포트폴리오 관리**: 관심 기업 즐겨찾기
4. **고급 필터링**: 업종, 규모별 필터

### 장기 목표 (6개월+)
1. **AI 분석**: 머신러닝 기반 재무분석
2. **모바일 앱**: React Native 앱 개발
3. **사용자 인증**: 개인화 서비스
4. **기업 평가**: 자동화된 기업가치 평가

## 🚨 DART API 사용 안내

### 필수 사항
- **API 키 발급**: https://opendart.fss.or.kr/
- **사용 제한**: 일일 20,000건, 초당 10건
- **데이터 범위**: 2015년 이후 상장회사

### 샘플 데이터 모드
API 키 없이도 삼성전자 기반 샘플 데이터로 모든 기능 체험 가능

## 🤝 기여하기

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 📧 문의

프로젝트에 대한 문의사항이 있으시면 이슈를 등록해 주세요.

---

⭐ 이 프로젝트가 도움이 되셨다면 Star를 눌러주세요! 