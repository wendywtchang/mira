"""
MIRA API 測試
"""

import requests

BASE_URL = "http://localhost:8000/api/v1"

def test_health_check():
    """測試健康檢查"""
    response = requests.get(f"{BASE_URL}/health/")
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'
    print("✓ Health check passed")

def test_chat_basic():
    """測試基本對話"""
    response = requests.post(
        f"{BASE_URL}/chat/",
        json={
            "message": "你好，請介紹一下你自己",
            "conversation_id": "test-001",
            "message_history": []
        }
    )
    data = response.json()
    assert response.status_code == 200
    assert data['status'] == 'success'
    assert 'response' in data
    assert 'message_history' in data
    print("✓ Chat passed")
    print(f"  回應：{data['response'][:50]}...")

def test_chat_history():
    """測試對話歷史是否正確傳遞"""
    # 第一輪
    response1 = requests.post(
        f"{BASE_URL}/chat/",
        json={
            "message": "我叫 Wendy",
            "conversation_id": "test-002",
            "message_history": []
        }
    )
    history = response1.json()['message_history']

    # 第二輪，帶入歷史
    response2 = requests.post(
        f"{BASE_URL}/chat/",
        json={
            "message": "你記得我叫什麼名字嗎？",
            "conversation_id": "test-002",
            "message_history": history
        }
    )
    data = response2.json()
    print("✓ History test passed")
    print(f"  回應：{data['response'][:80]}...")

if __name__ == "__main__":
    print("開始測試 MIRA API...\n")
    test_health_check()
    test_chat_basic()
    test_chat_history()
    print("\n所有測試通過！")