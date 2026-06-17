"""
MIRA - My Intelligent Research Assistant
"""
import os
import uuid
import requests
import chainlit as cl

DJANGO_API_BASE_URL = "http://localhost:8000/api/v1"

@cl.on_chat_start
async def on_chat_start():
    conversation_id = str(uuid.uuid4())
    cl.user_session.set("conversation_id", conversation_id)
    cl.user_session.set("message_history", [])
    
    # 加一個 RAG 模式開關
    settings = await cl.ChatSettings([
        cl.input_widget.Switch(
            id="use_rag",
            label="啟用知識庫 (RAG)",
            initial=False
        )
    ]).send()
    cl.user_session.set("use_rag", settings["use_rag"])

    try:
        health_check = requests.get(f"{DJANGO_API_BASE_URL}/health/", timeout=5)
        api_available = health_check.status_code == 200
    except Exception as e:
        api_available = False
        print(f"Django API connection failed: {e}")

    if api_available:
        welcome_msg = "Hello! I'm MIRA, your personal AI research assistant. How can I help you today?"
    else:
        welcome_msg = "Hello! I'm MIRA.\n\n⚠️ Warning: Unable to connect to backend. Please make sure Django is running."

    await cl.Message(content=welcome_msg).send()

@cl.on_settings_update
async def on_settings_update(settings):
    # 使用者切換 RAG 開關時更新 session，否則 use_rag 永遠是初始值
    cl.user_session.set("use_rag", settings["use_rag"])

@cl.on_message
async def on_message(message: cl.Message):
    conversation_id = cl.user_session.get("conversation_id")
    message_history = cl.user_session.get("message_history")

    thinking_msg = cl.Message(content="Thinking...")
    await thinking_msg.send()

    try:
        response = requests.post(
            f"{DJANGO_API_BASE_URL}/chat/",
            json={
                "message": message.content,
                "conversation_id": conversation_id,
                "message_history": message_history,
                "use_rag": cl.user_session.get("use_rag", False)
            },
            headers={"Content-Type": "application/json"},
            timeout=30
        )

        if response.status_code == 200:
            response_data = response.json()
            response_text = response_data.get("response", "")
            message_history = response_data.get("message_history", [])
            cl.user_session.set("message_history", message_history)

            await thinking_msg.remove()
            await cl.Message(content=response_text).send()

        else:
            error_message = f"API request failed: {response.status_code}"
            try:
                error_data = response.json()
                error_message += f" - {error_data.get('message', '')}"
            except:
                error_message += f" - {response.text}"

            await thinking_msg.remove()
            await cl.Message(content=error_message).send()

    except requests.exceptions.ConnectionError:
        await thinking_msg.remove()
        await cl.Message(content="Unable to connect to backend. Please make sure Django is running.").send()
        backup_response = generate_backup_response(message.content)
        await cl.Message(content=f"[Local backup response]: {backup_response}").send()

    except Exception as e:
        await thinking_msg.remove()
        await cl.Message(content=f"Error processing message: {str(e)}").send()


def generate_backup_response(message: str) -> str:
    message = message.lower()

    if "hello" in message or "hi" in message or "你好" in message:
        return "Hello! How can I help you?"
    elif "who are you" in message or "你是誰" in message:
        return "I'm MIRA, your personal AI research assistant."
    elif "thank" in message or "謝謝" in message:
        return "You're welcome!"
    elif "bye" in message or "goodbye" in message or "再見" in message:
        return "Goodbye! Feel free to come back anytime."
    else:
        return "Sorry, the backend service is currently unavailable. Please make sure Django is running."


if __name__ == "__main__":
    print("Starting MIRA, connecting to Django backend...")