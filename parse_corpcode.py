import xml.etree.ElementTree as ET
import sqlite3
import os

def create_database():
    """SQLite 데이터베이스 생성 및 테이블 생성"""
    conn = sqlite3.connect('companies.db')
    cursor = conn.cursor()
    
    # 회사 정보 테이블 생성
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS companies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        corp_code TEXT UNIQUE,
        corp_name TEXT,
        corp_name_eng TEXT,
        stock_code TEXT,
        modify_date TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    conn.commit()
    return conn

def parse_xml_file(filename):
    """XML 파일을 파싱하여 회사 정보 추출"""
    print(f"파싱 시작: {filename}")
    
    # XML 파일의 구조를 먼저 확인
    try:
        # 큰 파일이므로 iterparse를 사용하여 메모리 효율적으로 파싱
        companies = []
        
        for event, elem in ET.iterparse(filename, events=('start', 'end')):
            if event == 'end' and elem.tag == 'list':
                # 회사 정보 추출
                corp_code = elem.find('corp_code')
                corp_name = elem.find('corp_name')
                corp_name_eng = elem.find('corp_name_eng')
                stock_code = elem.find('stock_code')
                modify_date = elem.find('modify_date')
                
                company_data = {
                    'corp_code': corp_code.text if corp_code is not None else None,
                    'corp_name': corp_name.text if corp_name is not None else None,
                    'corp_name_eng': corp_name_eng.text if corp_name_eng is not None else None,
                    'stock_code': stock_code.text if stock_code is not None else None,
                    'modify_date': modify_date.text if modify_date is not None else None
                }
                
                companies.append(company_data)
                
                # 메모리 절약을 위해 처리된 요소 제거
                elem.clear()
                
                # 진행 상황 표시 (1000개마다)
                if len(companies) % 1000 == 0:
                    print(f"처리된 회사 수: {len(companies)}")
        
        return companies
    
    except ET.ParseError as e:
        print(f"XML 파싱 오류: {e}")
        return []
    except Exception as e:
        print(f"파일 처리 중 오류: {e}")
        return []

def save_to_database(companies, conn):
    """회사 정보를 데이터베이스에 저장"""
    cursor = conn.cursor()
    
    saved_count = 0
    error_count = 0
    
    for company in companies:
        try:
            cursor.execute('''
            INSERT OR REPLACE INTO companies 
            (corp_code, corp_name, corp_name_eng, stock_code, modify_date)
            VALUES (?, ?, ?, ?, ?)
            ''', (
                company['corp_code'],
                company['corp_name'],
                company['corp_name_eng'],
                company['stock_code'],
                company['modify_date']
            ))
            saved_count += 1
        except Exception as e:
            print(f"데이터 저장 오류: {e}, 회사: {company}")
            error_count += 1
    
    conn.commit()
    print(f"저장 완료: {saved_count}개 회사, 오류: {error_count}개")

def main():
    """메인 실행 함수"""
    xml_file = 'CORPCODE.xml'
    
    if not os.path.exists(xml_file):
        print(f"파일을 찾을 수 없습니다: {xml_file}")
        return
    
    # 데이터베이스 생성
    conn = create_database()
    
    try:
        # XML 파일 파싱
        companies = parse_xml_file(xml_file)
        
        if companies:
            print(f"총 {len(companies)}개의 회사 정보를 찾았습니다.")
            
            # 데이터베이스에 저장
            save_to_database(companies, conn)
            
            # 저장된 데이터 확인
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM companies')
            count = cursor.fetchone()[0]
            print(f"데이터베이스에 총 {count}개의 회사가 저장되었습니다.")
            
            # 샘플 데이터 출력
            cursor.execute('SELECT * FROM companies LIMIT 5')
            sample_companies = cursor.fetchall()
            print("\n샘플 데이터:")
            for company in sample_companies:
                print(f"- {company[2]} ({company[1]}) - 주식코드: {company[4]}")
        else:
            print("회사 정보를 찾을 수 없습니다.")
    
    except Exception as e:
        print(f"처리 중 오류 발생: {e}")
    
    finally:
        conn.close()

if __name__ == "__main__":
    main() 