from flask import Flask, render_template, request, jsonify
import sqlite3
import json
import requests
from datetime import datetime
import re
import os
from dotenv import load_dotenv
from openai import OpenAI

# 환경 변수 로드
print("현재 작업 디렉토리:", os.getcwd())
print(".env 파일 존재 여부:", os.path.exists('.env'))
load_dotenv(override=True)

app = Flask(__name__)

# OpenAI API 설정
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
print("OPENAI_API_KEY 존재 여부:", OPENAI_API_KEY is not None)
print("OPENAI_API_KEY 길이:", len(OPENAI_API_KEY) if OPENAI_API_KEY else 0)

# OpenAI 클라이언트 초기화
openai_client = None
if OPENAI_API_KEY:
    try:
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
        print("OpenAI 클라이언트 초기화 성공")
    except Exception as e:
        print(f"OpenAI 클라이언트 초기화 실패: {e}")
else:
    print("OpenAI API 키가 없어 클라이언트를 초기화하지 않습니다.")

# DART Open API 설정
DART_API_KEY = os.getenv('DART_API_KEY')
print("DART_API_KEY 존재 여부:", DART_API_KEY is not None)
print("DART_API_KEY 길이:", len(DART_API_KEY) if DART_API_KEY else 0)
if not DART_API_KEY:
    print("Warning: DART_API_KEY not found in environment variables")
DART_API_BASE_URL = "https://opendart.fss.or.kr/api"

# API 응답 상태 코드
DART_STATUS_CODES = {
    '000': '정상',
    '010': '등록되지 않은 키입니다.',
    '011': '사용할 수 없는 키입니다.',
    '012': '접근할 수 없는 IP입니다.',
    '013': '조회된 데이터가 없습니다.',
    '014': '파일이 존재하지 않습니다.',
    '020': '요청 제한을 초과하였습니다.',
    '100': '필드의 부적절한 값입니다.',
    '800': '시스템 점검 중입니다.',
    '900': '정의되지 않은 오류가 발생하였습니다.'
}

def get_db_connection():
    """데이터베이스 연결"""
    db_path = os.path.join(os.getenv('DATA_PATH', ''), 'companies.db')
    if not os.path.exists(db_path):
        # 데이터베이스 파일이 없으면 현재 디렉토리의 파일을 복사
        import shutil
        current_db = 'companies.db'
        if os.path.exists(current_db):
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            shutil.copy2(current_db, db_path)
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def clean_number(value):
    """숫자 데이터 정리 (콤마 제거 및 float 변환)"""
    if not value:
        return 0.0
    try:
        # 콤마 제거 후 float 변환
        cleaned = str(value).replace(',', '').replace(' ', '')
        return float(cleaned) if cleaned else 0.0
    except (ValueError, TypeError):
        return 0.0

def format_amount(amount):
    """금액을 조원/억원 단위로 포맷"""
    try:
        num = float(amount)
        if num >= 1000000000000:  # 1조 이상
            return f"{num/1000000000000:.1f}조원"
        elif num >= 100000000:  # 1억 이상
            return f"{num/100000000:.0f}억원"
        else:
            return f"{num:,.0f}원"
    except:
        return str(amount)

def get_financial_data(corp_code, bsns_year="2023", reprt_code="11011"):
    """DART API에서 재무정보 가져오기"""
    if not DART_API_KEY:
        print("DART API 키가 없습니다!")
        return {
            'status': 'error',
            'message': 'DART API 키가 설정되지 않았습니다.',
            'data': []
        }

    try:
        # DART API 엔드포인트 직접 호출
        url = "https://opendart.fss.or.kr/api/fnlttSinglAcnt.json"
        params = {
            'crtfc_key': DART_API_KEY,
            'corp_code': corp_code,
            'bsns_year': bsns_year,
            'reprt_code': reprt_code
        }
        
        print("\n=== DART API 요청 정보 ===")
        print(f"URL: {url}")
        print(f"API Key: {DART_API_KEY}")
        print(f"기업코드: {corp_code}")
        print(f"사업연도: {bsns_year}")
        print(f"보고서 코드: {reprt_code}")
        
        # 실제 요청 URL 출력 (디버깅용)
        full_url = f"{url}?crtfc_key={DART_API_KEY}&corp_code={corp_code}&bsns_year={bsns_year}&reprt_code={reprt_code}"
        print(f"전체 URL: {full_url}")
        print("========================\n")
        
        response = requests.get(url, params=params, timeout=10)
        print(f"응답 상태 코드: {response.status_code}")
        print(f"실제 요청 URL: {response.url}")
        
        response.raise_for_status()
        data = response.json()
        
        print(f"API 응답: {data.get('status')} - {DART_STATUS_CODES.get(data.get('status'), '알 수 없는 상태')}")
        
        status = data.get('status')
        if status == '000':
            # 연결재무제표와 개별재무제표 분리
            cfs_data = [item for item in data.get('list', []) if item.get('fs_div') == 'CFS']
            ofs_data = [item for item in data.get('list', []) if item.get('fs_div') == 'OFS']
            
            # 재무상태표와 손익계산서 분리
            financial_data = {
                'cfs': {
                    'bs': [item for item in cfs_data if item.get('sj_div') == 'BS'],
                    'is': [item for item in cfs_data if item.get('sj_div') == 'IS']
                },
                'ofs': {
                    'bs': [item for item in ofs_data if item.get('sj_div') == 'BS'],
                    'is': [item for item in ofs_data if item.get('sj_div') == 'IS']
                }
            }
            
            return {
                'status': 'success',
                'message': DART_STATUS_CODES.get(status, '알 수 없는 상태'),
                'data': financial_data
            }
        else:
            error_message = DART_STATUS_CODES.get(status, '알 수 없는 오류')
            print(f"DART API 오류 ({status}): {error_message}")
            return {
                'status': 'error',
                'message': f"DART API 오류: {error_message}",
                'data': []
            }
            
    except requests.exceptions.Timeout:
        print("DART API 요청 시간 초과")
        return {
            'status': 'error',
            'message': 'DART API 요청 시간이 초과되었습니다.',
            'data': []
        }
    except requests.exceptions.RequestException as e:
        print(f"DART API 요청 오류: {e}")
        return {
            'status': 'error',
            'message': 'DART API 요청 중 오류가 발생했습니다.',
            'data': []
        }
    except Exception as e:
        print(f"재무정보 조회 오류: {e}")
        return {
            'status': 'error',
            'message': '재무정보를 처리하는 중 오류가 발생했습니다.',
            'data': []
        }

def calculate_financial_ratios(financial_data):
    """재무비율 계산"""
    ratios = {}
    
    try:
        # 연결재무제표 데이터 사용
        bs_data = financial_data['cfs']['bs']
        is_data = financial_data['cfs']['is']
        
        # 주요 계정 찾기
        def find_account(data, account_name):
            for item in data:
                if item.get('account_nm') == account_name:
                    return {
                        'current': clean_number(item.get('thstrm_amount', 0)),
                        'previous': clean_number(item.get('frmtrm_amount', 0)),
                        'previous2': clean_number(item.get('bfefrmtrm_amount', 0))
                    }
            return {'current': 0, 'previous': 0, 'previous2': 0}
        
        # 재무상태표 계정
        assets = find_account(bs_data, '자산총계')
        liabilities = find_account(bs_data, '부채총계')
        equity = find_account(bs_data, '자본총계')
        current_assets = find_account(bs_data, '유동자산')
        current_liabilities = find_account(bs_data, '유동부채')
        
        # 손익계산서 계정
        revenue = find_account(is_data, '매출액')
        operating_profit = find_account(is_data, '영업이익')
        net_income = find_account(is_data, '당기순이익')
        
        # 수익성 비율 계산
        if revenue['current'] > 0:
            ratios['operating_margin'] = round((operating_profit['current'] / revenue['current']) * 100, 1)
            ratios['net_margin'] = round((net_income['current'] / revenue['current']) * 100, 1)
        
        # 안정성 비율 계산
        if equity['current'] > 0:
            ratios['debt_ratio'] = round((liabilities['current'] / equity['current']) * 100, 1)
            ratios['roe'] = round((net_income['current'] / equity['current']) * 100, 1)
        
        if assets['current'] > 0:
            ratios['roa'] = round((net_income['current'] / assets['current']) * 100, 1)
            ratios['equity_ratio'] = round((equity['current'] / assets['current']) * 100, 1)
        
        if current_liabilities['current'] > 0:
            ratios['current_ratio'] = round((current_assets['current'] / current_liabilities['current']) * 100, 1)
        
        # 기본 수치 저장 (포맷된 형태)
        ratios['revenue_formatted'] = format_amount(revenue['current'])
        ratios['operating_profit_formatted'] = format_amount(operating_profit['current'])
        ratios['net_income_formatted'] = format_amount(net_income['current'])
        ratios['total_assets_formatted'] = format_amount(assets['current'])
        ratios['total_liabilities_formatted'] = format_amount(liabilities['current'])
        ratios['total_equity_formatted'] = format_amount(equity['current'])
            
    except Exception as e:
        print(f"재무비율 계산 오류: {e}")
    
    return ratios

def get_chart_data(financial_data):
    """차트용 데이터 추출"""
    chart_data = {}
    
    try:
        # 연결재무제표 데이터 사용
        bs_data = financial_data['cfs']['bs']
        is_data = financial_data['cfs']['is']
        
        def find_account(data, account_name):
            for item in data:
                if item.get('account_nm') == account_name:
                    return {
                        'current': clean_number(item.get('thstrm_amount', 0)),
                        'previous': clean_number(item.get('frmtrm_amount', 0)),
                        'previous2': clean_number(item.get('bfefrmtrm_amount', 0))
                    }
            return {'current': 0, 'previous': 0, 'previous2': 0}
        
        # 재무상태표 데이터 (조원 단위)
        assets = find_account(bs_data, '자산총계')
        liabilities = find_account(bs_data, '부채총계')
        equity = find_account(bs_data, '자본총계')
        
        chart_data['balance'] = {
            'labels': ['자산총계', '부채총계', '자본총계'],
            'data': [
                round(assets['current'] / 1000000000000, 1),
                round(liabilities['current'] / 1000000000000, 1),
                round(equity['current'] / 1000000000000, 1)
            ]
        }
        
        # 매출액 추이 (조원 단위)
        revenue = find_account(is_data, '매출액')
        chart_data['revenue_trend'] = {
            'labels': ['전전기', '전기', '당기'],
            'data': [
                round(revenue['previous2'] / 1000000000000, 1),
                round(revenue['previous'] / 1000000000000, 1),
                round(revenue['current'] / 1000000000000, 1)
            ]
        }
        
        # 이익 추이 (조원 단위)
        operating_profit = find_account(is_data, '영업이익')
        net_income = find_account(is_data, '당기순이익')
        
        chart_data['profit_trend'] = {
            'labels': ['전전기', '전기', '당기'],
            'operating_profit': [
                round(operating_profit['previous2'] / 1000000000000, 1),
                round(operating_profit['previous'] / 1000000000000, 1),
                round(operating_profit['current'] / 1000000000000, 1)
            ],
            'net_income': [
                round(net_income['previous2'] / 1000000000000, 1),
                round(net_income['previous'] / 1000000000000, 1),
                round(net_income['current'] / 1000000000000, 1)
            ]
        }
        
    except Exception as e:
        print(f"차트 데이터 생성 오류: {e}")
    
    return chart_data

def generate_financial_report(company_info, financial_data, ratios):
    """AI를 사용하여 재무 보고서 생성"""
    try:
        if not openai_client:
            print("OpenAI 클라이언트가 초기화되지 않았습니다.")
            return {
                'status': 'error',
                'message': 'OpenAI API 키가 설정되지 않았거나 유효하지 않습니다.'
            }

        # 프롬프트 구성
        prompt = f"""
회사명: {company_info['corp_name']}
업종: {company_info.get('industry', '정보 없음')}

주요 재무 지표:
- 매출액: {ratios.get('revenue_formatted', '정보 없음')}
- 영업이익: {ratios.get('operating_profit_formatted', '정보 없음')}
- 당기순이익: {ratios.get('net_income_formatted', '정보 없음')}
- 자산총계: {ratios.get('total_assets_formatted', '정보 없음')}
- 부채총계: {ratios.get('total_liabilities_formatted', '정보 없음')}
- 자본총계: {ratios.get('total_equity_formatted', '정보 없음')}

재무비율:
- 영업이익률: {ratios.get('operating_margin', '정보 없음')}%
- 순이익률: {ratios.get('net_margin', '정보 없음')}%
- ROE(자기자본이익률): {ratios.get('roe', '정보 없음')}%
- ROA(총자산이익률): {ratios.get('roa', '정보 없음')}%
- 부채비율: {ratios.get('debt_ratio', '정보 없음')}%
- 자기자본비율: {ratios.get('equity_ratio', '정보 없음')}%
- 유동비율: {ratios.get('current_ratio', '정보 없음')}%

위 정보를 바탕으로 다음 내용을 포함하는 전문적인 재무 분석 보고서를 작성해주세요:
1. 회사 개요 및 현재 재무상태 요약
2. 수익성 분석
3. 재무안정성 분석
4. 투자 관점에서의 주요 시사점
5. 향후 주의해야 할 리스크 요인
"""

        print("\n=== OpenAI SDK 요청 정보 ===")
        print(f"클라이언트 상태: {'초기화됨' if openai_client else '초기화 안됨'}")
        print(f"모델: gpt-3.5-turbo")
        print("========================\n")

        # OpenAI SDK 사용
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",  # 더 안정적인 모델 사용
            messages=[
                {"role": "system", "content": "당신은 전문 재무분석가입니다. 주어진 재무정보를 바탕으로 객관적이고 통찰력 있는 분석 보고서를 작성해주세요."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000,
            timeout=60  # 타임아웃을 60초로 증가
        )
        
        print("OpenAI API 호출 성공")
        
        report = response.choices[0].message.content
        return {
            'status': 'success',
            'report': report
        }
            
    except Exception as e:
        print(f"AI 보고서 생성 오류: {e}")
        return {
            'status': 'error',
            'message': f'AI 보고서 생성 중 오류가 발생했습니다: {str(e)}'
        }

@app.route('/')
def index():
    """메인 페이지"""
    return render_template('index.html')

@app.route('/company/<corp_code>')
def company_detail(corp_code):
    """회사 상세 페이지"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 회사 기본 정보 조회
    cursor.execute('SELECT * FROM companies WHERE corp_code = ?', (corp_code,))
    company = cursor.fetchone()
    conn.close()
    
    if not company:
        return "회사를 찾을 수 없습니다.", 404
    
    # 주식코드가 없는 회사는 재무정보 접근 불가
    if not company['stock_code'] or not company['stock_code'].strip():
        return render_template('company_detail.html', 
                             company=dict(company), 
                             is_unlisted=True)
    
    return render_template('company_detail.html', 
                         company=dict(company), 
                         is_unlisted=False)

@app.route('/api/financial/<corp_code>')
def get_company_financial(corp_code):
    """회사 재무정보 API"""
    # 주식코드 확인
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM companies WHERE corp_code = ?', (corp_code,))
    company = cursor.fetchone()
    conn.close()
    
    if not company or not company['stock_code'] or not company['stock_code'].strip():
        return jsonify({'error': '비상장회사는 재무정보를 제공하지 않습니다.'}), 400
    
    year = request.args.get('year', '2023')
    report_type = request.args.get('report_type', '11011')  # 사업보고서
    
    # DART API에서 재무데이터 조회
    financial_result = get_financial_data(corp_code, year, report_type)
    
    if financial_result['status'] == 'error':
        return jsonify({
            'error': financial_result['message'],
            'financial_ratios': {},
            'chart_data': {},
            'table_data': [],
            'raw_data': [],
            'ai_report': {
                'status': 'error',
                'message': '재무정보를 불러올 수 없어 AI 분석을 수행할 수 없습니다.'
            }
        })

    financial_data = financial_result['data']
    
    # 재무비율 계산
    ratios = calculate_financial_ratios(financial_data)
    
    # 차트용 데이터 생성
    chart_data = get_chart_data(financial_data)
    
    # 재무제표 테이블용 데이터
    table_data = []
    key_accounts = ['매출액', '영업이익', '당기순이익', '자산총계', '부채총계', '자본총계']
    
    # 재무상태표와 손익계산서 모두에서 찾기
    all_items = financial_data['cfs']['bs'] + financial_data['cfs']['is']
    
    for account in key_accounts:
        for item in all_items:
            if item.get('account_nm') == account:
                table_data.append({
                    'account_nm': item.get('account_nm'),
                    'thstrm_amount': format_amount(clean_number(item.get('thstrm_amount', 0))),
                    'frmtrm_amount': format_amount(clean_number(item.get('frmtrm_amount', 0))),
                    'bfefrmtrm_amount': format_amount(clean_number(item.get('bfefrmtrm_amount', 0)))
                })
                break
    
    return jsonify({
        'financial_ratios': ratios,
        'chart_data': chart_data,
        'table_data': table_data,
        'raw_data': financial_data['cfs']['bs'][:10],  # 상위 10개만
        'ai_report': {
            'status': 'disabled',
            'message': 'AI 분석 보고서 기능이 현재 비활성화되어 있습니다. OpenAI API 키를 설정해주세요.'
        }
    })

@app.route('/api/financial/<corp_code>/ai_report')
def get_ai_report(corp_code):
    """AI 분석 보고서 생성 API"""
    try:
        # 회사 정보 조회
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM companies WHERE corp_code = ?', (corp_code,))
        company = cursor.fetchone()
        conn.close()
        
        if not company:
            return jsonify({
                'status': 'error',
                'message': '회사를 찾을 수 없습니다.'
            }), 404
        
        # 비상장회사 체크
        if not company['stock_code'] or not company['stock_code'].strip():
            return jsonify({
                'status': 'error',
                'message': '비상장회사는 AI 분석 보고서를 제공하지 않습니다.'
            }), 400
        
        year = request.args.get('year', '2023')
        report_type = request.args.get('report_type', '11011')
        
        # 재무데이터 조회
        financial_result = get_financial_data(corp_code, year, report_type)
        if financial_result['status'] == 'error':
            return jsonify({
                'status': 'error',
                'message': f'재무정보 조회 실패: {financial_result["message"]}'
            }), 400
            
        financial_data = financial_result['data']
        ratios = calculate_financial_ratios(financial_data)
        
        # AI 보고서 생성
        ai_report = generate_financial_report(dict(company), financial_data, ratios)
        
        return jsonify(ai_report)
        
    except Exception as e:
        print(f"AI 보고서 API 오류: {e}")
        return jsonify({
            'status': 'error',
            'message': 'AI 보고서 생성 중 서버 오류가 발생했습니다.'
        }), 500

@app.route('/api/companies')
def get_companies():
    """회사 목록 API"""
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    search = request.args.get('search', '')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 검색 조건에 따라 전체 개수 먼저 조회
    if search:
        # 전체 검색 결과 수
        count_query = '''
        SELECT COUNT(*) FROM companies 
        WHERE corp_name LIKE ? OR corp_code LIKE ? OR stock_code LIKE ?
        '''
        search_term = f'%{search}%'
        cursor.execute(count_query, (search_term, search_term, search_term))
        total = cursor.fetchone()[0]
        
        # 페이지네이션된 검색 결과
        query = '''
        SELECT * FROM companies 
        WHERE corp_name LIKE ? OR corp_code LIKE ? OR stock_code LIKE ?
        ORDER BY corp_name
        LIMIT ? OFFSET ?
        '''
        cursor.execute(query, (search_term, search_term, search_term, per_page, (page-1)*per_page))
    else:
        # 전체 회사 수
        cursor.execute('SELECT COUNT(*) FROM companies')
        total = cursor.fetchone()[0]
        
        # 페이지네이션된 전체 결과
        query = 'SELECT * FROM companies ORDER BY corp_name LIMIT ? OFFSET ?'
        cursor.execute(query, (per_page, (page-1)*per_page))
    
    companies = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return jsonify({
        'companies': companies,
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page
    })

@app.route('/api/company/<corp_code>')
def get_company(corp_code):
    """특정 회사 정보 API"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM companies WHERE corp_code = ?', (corp_code,))
    company = cursor.fetchone()
    
    conn.close()
    
    if company:
        return jsonify(dict(company))
    else:
        return jsonify({'error': '회사를 찾을 수 없습니다'}), 404

@app.route('/api/stats')
def get_stats():
    """통계 정보 API"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 전체 회사 수
    cursor.execute('SELECT COUNT(*) FROM companies')
    total_companies = cursor.fetchone()[0]
    
    # 실제 상장회사 수 (주식코드가 있는 회사)
    cursor.execute("SELECT COUNT(*) FROM companies WHERE LENGTH(TRIM(COALESCE(stock_code, ''))) > 0")
    listed_companies = cursor.fetchone()[0]
    
    # 비상장회사 수
    unlisted_companies = total_companies - listed_companies
    
    # 최근 수정된 회사들
    cursor.execute('''
    SELECT corp_name, modify_date 
    FROM companies 
    WHERE modify_date IS NOT NULL 
    ORDER BY modify_date DESC 
    LIMIT 10
    ''')
    recent_updates = [dict(row) for row in cursor.fetchall()]
    
    # 주요 상장회사 샘플
    cursor.execute('''
    SELECT corp_name, stock_code 
    FROM companies 
    WHERE LENGTH(TRIM(COALESCE(stock_code, ''))) > 0
    ORDER BY corp_name
    LIMIT 10
    ''')
    sample_listed = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return jsonify({
        'total_companies': total_companies,
        'listed_companies': listed_companies,
        'unlisted_companies': unlisted_companies,
        'recent_updates': recent_updates,
        'sample_listed': sample_listed
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port) 