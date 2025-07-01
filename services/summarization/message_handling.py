from datetime import datetime, timedelta
import traceback
from .db import db, DR_JIB_CONVERSATIONS_COLLECTION  # Assuming db is part of summarization service
from .qiscus_misc import send_message_to_qiscus, send_image_to_qiscus
from services.dr_jib.dr_jib_service import dr_jib_response
import asyncio
import re

# Configuration
MAX_MESSAGES_PER_SESSION = 5

def remove_markdown_elements(content: str) -> str:
    # Remove code blocks (```...```)
    cleaned_content = re.sub(r"```.*?```", "", content, flags=re.DOTALL)

    # Remove inline code (`...`)
    cleaned_content = re.sub(r"`([^`]*)`", r"\1", cleaned_content)

    # Remove headers (e.g., # Header)
    cleaned_content = re.sub(r"^\s*#+\s*(.*)", r"\1", cleaned_content, flags=re.MULTILINE)

    # Remove bold and italic (**text**, *text*, __text__, _text_)
    cleaned_content = re.sub(r"\*\*(.*?)\*\*", r"\1", cleaned_content)
    cleaned_content = re.sub(r"\*(.*?)\*", r"\1", cleaned_content)

    return cleaned_content.strip()

def process_messages_batch(room_id):
    try:
        conv_ref = db.collection(DR_JIB_CONVERSATIONS_COLLECTION).document(room_id)
        conv_doc = conv_ref.get()

        if not conv_doc.exists:
            print(f"No conversation history found for {room_id}")
            return
        
        conversation_history = conv_doc.to_dict()
        messages = conversation_history.get("messages", [])
        print(messages)

        # Keep only the most recent image and text messages by removing all previous messages except the last image and text message
        last_image_index = -1
        for i, msg in enumerate(reversed(messages)):
            if (
                isinstance(msg["content"], list)
                and msg["content"][0]["type"] == "image_url"
            ):
                last_image_index = len(messages) - 1 - i
                break

        if last_image_index != -1:
            messages = [
                msg
                for i, msg in enumerate(messages)
                if i == last_image_index or isinstance(msg["content"], str)
            ]

        messages = messages[-MAX_MESSAGES_PER_SESSION:]
        # check for last seen nudge message
        nudge = True  # Initialize default value
        for message in reversed(messages):
            if "https://i.hdmall.co.th/ha-app" in message["content"]:
                print("found nudge message")
                try:
                    last_nudge_message_timestamp = message["timestamp"]
                    last_nudge_message_timestamp = datetime.strptime(last_nudge_message_timestamp, "%Y-%m-%dT%H:%M:%S.%f")
                    time_difference = datetime.now() - last_nudge_message_timestamp
                    nudge = time_difference > timedelta(days=7)
                    break  # Exit loop after finding and processing the first nudge message
                except Exception as e:
                    print(f"Error for {room_id} at message {str(message)}: {str(e)}")
                
        response_message = asyncio.run(dr_jib_response(messages=messages, room_id=room_id, nudge=nudge))
        response_message = remove_markdown_elements(response_message)

        if not response_message:
            print(f"Unable to get response from GPT for {room_id} : {response_message}")
        else:
            current_time = datetime.now()
            conversation_history["messages"].append(
                {"content": response_message, "role": "assistant", "timestamp": current_time.isoformat()}
            )
            target_text = "ในกรณีฉุกเฉิน โทร 1724 (กรุงเทพฯ) หรือ 1669 (ประเทศไทย) สำหรับการสนับสนุนด้านสุขภาพจิต โทร 1323"
            replace_text = "ในกรณีฉุกเฉิน โทร 1669 (ประเทศไทย) สำหรับการสนับสนุนด้านสุขภาพจิต โทร 1323"
            if target_text in response_message:
                response_message = response_message.replace(target_text, replace_text)
            send_message_to_qiscus(response_message, room_id)
            #TODO 
            #if nudge is true, and app promo message is in the response, send image to qiscus
            if nudge and "https://i.hdmall.co.th/ha-app" in response_message:
                send_image_to_qiscus(room_id)
            conv_ref.set(conversation_history)

    except Exception as e:
        print(f"Error for {room_id}: {str(e)}")
        traceback.print_exc()
        send_message_to_qiscus(
            "ดูเหมือนจิ๊บจะกำลังติดธุระ เรากำลังติดต่อแอดมินเพื่อช่วยเหลือคุณ.", room_id
        )
        current_time = datetime.now()
        conv_ref.set(
            {
                "messages": [],
                "last_message_time": current_time.isoformat()
            }
        )
        print(f"Clearing history for {room_id} and test again...") 