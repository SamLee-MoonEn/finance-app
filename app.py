from flask import Flask, render_template, request, jsonify
import sqlite3
import json
import requests
from datetime import datetime
import re
import os
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

app = Flask(__name__)

# OpenAI API 설정
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# DART Open API 설정
DART_API_KEY = os.getenv('DART_API_KEY')
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
        return {
            'status': 'error',
            'message': 'DART API 키가 설정되지 않았습니다.',
            'data': []
        }

    try:
        url = f"{DART_API_BASE_URL}/fnlttSinglAcnt.json"
        params = {
            'crtfc_key': DART_API_KEY,
            'corp_code': corp_code,
            'bsns_year': bsns_year,
            'reprt_code': reprt_code
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()  # HTTP 에러 체크
        data = response.json()
        
        status = data.get('status')
        if status == '000':
            return {
                'status': 'success',
                'message': DART_STATUS_CODES.get(status, '알 수 없는 상태'),
                'data': data.get('list', [])
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
    
    # 재무데이터를 계정명으로 인덱싱 (연결재무제표 우선)
    accounts = {}
    for item in financial_data:
        if item.get('fs_div') == 'CFS':  # 연결재무제표 우선
            account_name = item.get('account_nm')
            accounts[account_name] = item
    
    # 연결재무제표가 없으면 개별재무제표 사용
    if not accounts:
        for item in financial_data:
            if item.get('fs_div') == 'OFS':  # 개별재무제표
                account_name = item.get('account_nm')
                accounts[account_name] = item
    
    try:
        # 주요 계정 추출 및 숫자 변환
        revenue = clean_number(accounts.get('매출액', {}).get('thstrm_amount', 0))
        operating_profit = clean_number(accounts.get('영업이익', {}).get('thstrm_amount', 0))
        net_income = clean_number(accounts.get('당기순이익', {}).get('thstrm_amount', 0))
        total_assets = clean_number(accounts.get('자산총계', {}).get('thstrm_amount', 0))
        total_liabilities = clean_number(accounts.get('부채총계', {}).get('thstrm_amount', 0))
        total_equity = clean_number(accounts.get('자본총계', {}).get('thstrm_amount', 0))
        current_assets = clean_number(accounts.get('유동자산', {}).get('thstrm_amount', 0))
        current_liabilities = clean_number(accounts.get('유동부채', {}).get('thstrm_amount', 0))
        
        # 수익성 비율 계산
        if revenue > 0:
            ratios['operating_margin'] = round((operating_profit / revenue) * 100, 1)
            ratios['net_margin'] = round((net_income / revenue) * 100, 1)
        
        # 안정성 비율 계산
        if total_equity > 0:
            ratios['debt_ratio'] = round((total_liabilities / total_equity) * 100, 1)
            ratios['roe'] = round((net_income / total_equity) * 100, 1)
        
        if total_assets > 0:
            ratios['roa'] = round((net_income / total_assets) * 100, 1)
            ratios['equity_ratio'] = round((total_equity / total_assets) * 100, 1)
        
        if current_liabilities > 0:
            ratios['current_ratio'] = round((current_assets / current_liabilities) * 100, 1)
        
        # 기본 수치 저장 (포맷된 형태)
        ratios['revenue_formatted'] = format_amount(revenue)
        ratios['operating_profit_formatted'] = format_amount(operating_profit)
        ratios['net_income_formatted'] = format_amount(net_income)
        ratios['total_assets_formatted'] = format_amount(total_assets)
        ratios['total_liabilities_formatted'] = format_amount(total_liabilities)
        ratios['total_equity_formatted'] = format_amount(total_equity)
            
    except Exception as e:
        print(f"재무비율 계산 오류: {e}")
    
    return ratios

def get_chart_data(financial_data):
    """차트용 데이터 추출"""
    chart_data = {}
    
    # 연결재무제표 우선 선택
    accounts = {}
    for item in financial_data:
        if item.get('fs_div') == 'CFS':
            account_name = item.get('account_nm')
            accounts[account_name] = item
    
    if not accounts:  # 연결재무제표가 없으면 개별재무제표
        for item in financial_data:
            if item.get('fs_div') == 'OFS':
                account_name = item.get('account_nm')
                accounts[account_name] = item
    
    try:
        # 자산/부채/자본 구성 (조원 단위)
        total_assets = clean_number(accounts.get('자산총계', {}).get('thstrm_amount', 0)) / 1000000000000
        total_liabilities = clean_number(accounts.get('부채총계', {}).get('thstrm_amount', 0)) / 1000000000000
        total_equity = clean_number(accounts.get('자본총계', {}).get('thstrm_amount', 0)) / 1000000000000
        
        chart_data['balance'] = {
            'labels': ['자산총계', '부채총계', '자본총계'],
            'data': [round(total_assets, 1), round(total_liabilities, 1), round(total_equity, 1)]
        }
        
        # 매출액 3년 추이 (조원 단위)
        revenue_current = clean_number(accounts.get('매출액', {}).get('thstrm_amount', 0)) / 1000000000000
        revenue_prev = clean_number(accounts.get('매출액', {}).get('frmtrm_amount', 0)) / 1000000000000
        revenue_prev2 = clean_number(accounts.get('매출액', {}).get('bfefrmtrm_amount', 0)) / 1000000000000
        
        chart_data['revenue_trend'] = {
            'labels': ['전전기', '전기', '당기'],
            'data': [round(revenue_prev2, 1), round(revenue_prev, 1), round(revenue_current, 1)]
        }
        
        # 이익 3년 추이 (조원 단위)
        op_current = clean_number(accounts.get('영업이익', {}).get('thstrm_amount', 0)) / 1000000000000
        op_prev = clean_number(accounts.get('영업이익', {}).get('frmtrm_amount', 0)) / 1000000000000
        op_prev2 = clean_number(accounts.get('영업이익', {}).get('bfefrmtrm_amount', 0)) / 1000000000000
        
        net_current = clean_number(accounts.get('당기순이익', {}).get('thstrm_amount', 0)) / 1000000000000
        net_prev = clean_number(accounts.get('당기순이익', {}).get('frmtrm_amount', 0)) / 1000000000000
        net_prev2 = clean_number(accounts.get('당기순이익', {}).get('bfefrmtrm_amount', 0)) / 1000000000000
        
        chart_data['profit_trend'] = {
            'labels': ['전전기', '전기', '당기'],
            'operating_profit': [round(op_prev2, 1), round(op_prev, 1), round(op_current, 1)],
            'net_income': [round(net_prev2, 1), round(net_prev, 1), round(net_current, 1)]
        }
        
    except Exception as e:
        print(f"차트 데이터 생성 오류: {e}")
    
    return chart_data

def generate_financial_report(company_info, financial_data, ratios):
    """AI를 사용하여 재무 보고서 생성"""
    try:
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

        # OpenAI API 직접 호출
        headers = {
            'Authorization': f'Bearer {OPENAI_API_KEY}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'model': 'gpt-4-turbo-preview',
            'messages': [
                {'role': 'system', 'content': '당신은 전문 재무분석가입니다. 주어진 재무정보를 바탕으로 객관적이고 통찰력 있는 분석 보고서를 작성해주세요.'},
                {'role': 'user', 'content': prompt}
            ],
            'temperature': 0.7,
            'max_tokens': 2000
        }
        
        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            report = response.json()['choices'][0]['message']['content']
            return {
                'status': 'success',
                'report': report
            }
        else:
            print(f"OpenAI API 오류: {response.status_code}")
            return {
                'status': 'error',
                'message': 'AI 보고서 생성 중 오류가 발생했습니다.'
            }
            
    except Exception as e:
        print(f"AI 보고서 생성 오류: {e}")
        return {
            'status': 'error',
            'message': '보고서 생성 중 오류가 발생했습니다.'
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
            'financial_summary': [],
            'financial_ratios': {},
            'chart_data': {},
            'raw_data': []
        })

    financial_data = financial_result['data']
    
    # 재무비율 계산
    ratios = calculate_financial_ratios(financial_data)
    
    # 차트용 데이터 생성
    chart_data = get_chart_data(financial_data)
    
    # AI 보고서 생성
    ai_report = generate_financial_report(dict(company), financial_data, ratios)
    
    # 재무제표 테이블용 데이터
    table_data = []
    key_accounts = ['매출액', '영업이익', '당기순이익', '자산총계', '부채총계', '자본총계']
    
    for item in financial_data:
        if item.get('fs_div') == 'CFS' and item.get('account_nm') in key_accounts:
            table_data.append({
                'account_nm': item.get('account_nm'),
                'thstrm_amount': format_amount(clean_number(item.get('thstrm_amount', 0))),
                'frmtrm_amount': format_amount(clean_number(item.get('frmtrm_amount', 0))),
                'bfefrmtrm_amount': format_amount(clean_number(item.get('bfefrmtrm_amount', 0)))
            })
    
    return jsonify({
        'financial_ratios': ratios,
        'chart_data': chart_data,
        'table_data': table_data,
        'ai_report': ai_report,
        'raw_data': financial_data[:10]  # 상위 10개만
    })

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