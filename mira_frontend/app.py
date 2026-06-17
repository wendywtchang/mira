"""
MIRA - My Intelligent Research Assistant

"""
import os
import sys
import uuid
import chainlit as cl

@cl.on_chat_start
async def on_chat_start():
    """當用戶開始新對話時執行"""
    # 創建會話ID
    conversation_id = str(uuid.uuid4())
    cl.user_session.set("conversation_id", conversation_id)
    
    # 初始化消息歷史
    cl.user_session.set("message_history", [])
    
    # 發送歡迎訊息
    await cl.Message(
        content="您好！我是 Mira，您任勞任怨的RA。"
    ).send()

@cl.on_message
async def on_message(message: cl.Message):
    """處理用戶發送的訊息"""
    # 獲取會話數據
    conversation_id = cl.user_session.get("conversation_id")
    message_history = cl.user_session.get("message_history")
    
    # 顯示思考中的狀態
    thinking_msg = cl.Message(content="I'm thinking...")
    await thinking_msg.send()
    
    # 模擬AI處理和回覆
    # 由於這是基礎版本，我們暫時使用簡單回應
    user_message = message.content
    
    # 添加用戶訊息到歷史記錄
    message_history.append({"role": "user", "content": user_message})
    
    # 處理簡單響應邏輯
    response_text = generate_simple_response(user_message)
    
    # 添加助手回應到歷史記錄
    message_history.append({"role": "assistant", "content": response_text})
    
    # 更新會話歷史
    cl.user_session.set("message_history", message_history)
    
    # 移除思考中的消息
    await thinking_msg.remove()
    
    # 發送回應
    await cl.Message(content=response_text).send()

def generate_simple_response(message: str) -> str:
    """
    生成簡單的回應 (模擬實際的AI回應)
    """
    # 簡單關鍵詞匹配
    message = message.lower()
    
    if "你好" in message or "hi" in message or "hello" in message:
        return "你好！有什麼我可以幫助你的嗎？"
    
    elif "你是誰" in message or "你的名字" in message:
        return "您好！我是 Mira，您任勞任怨的RA。"
    
    elif "謝謝" in message or "thank you" in message or "thanks" in message:
        return "不用謝！很高興能夠幫到您。"
    
    elif "再見" in message or "goodbye" in message or "byebye" in message:
        return "再見！有需要隨時呼叫我。"
    
    else:
        return "抱歉，目前我把大腦忘在在家裡了，無法回答這個問題。"

if __name__ == "__main__":
    print("啟動MIRA，基礎對話界面...")