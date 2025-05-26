import requests
import json

def test_ai_api():
    url = "http://localhost:5000/api/financial/00126380/ai_report?year=2023"
    
    try:
        print("AI 보고서 API 테스트 중...")
        response = requests.get(url, timeout=30)
        
        print(f"상태 코드: {response.status_code}")
        print(f"응답 헤더: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"응답 데이터: {json.dumps(data, indent=2, ensure_ascii=False)}")
        else:
            print(f"오류 응답: {response.text}")
            
    except Exception as e:
        print(f"오류 발생: {e}")

if __name__ == "__main__":
    test_ai_api() 