import requests

def get_message(data):
    try:
        attachment = data.get("payload", {}).get("message", {}).get("payload", "")
        attachment_url = ""
        if attachment:
            attachment_url = attachment.get("url", "")
        if attachment_url and (
            attachment_url.endswith(".jpg")
            or attachment_url.endswith(".jpeg")
            or attachment_url.endswith(".png")
        ):
            return [
                {
                    "type": "image_url",
                    "image_url": {"url": attachment_url, "detail": "auto"},
                }
            ]
                
        else:
            return data.get("payload", {}).get("message", {}).get("text", "")
    except Exception as e:
        print(f"Error in get_message: {str(e)}")
        return data.get("payload", {}).get("message", {}).get("text", "")

def handle_agent_assignment(division, room_id):
    print("Handling agent assignment for division:", division)
    url = f"https://omnichannel.qiscus.com/daki-fq9mhonubqarcuy6/bot/{room_id}/hand_over_to_role"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "c7974edbd33f204f45e74b0f22c1ce15",
    }
    data = {"role": division, "find_online_agent": True}
    response = requests.post(url, json=data, headers=headers)
    print("Agent assignment response:", response.json())

def send_message_to_qiscus(message, room_id):
    url = "https://omnichannel.qiscus.com/daki-fq9mhonubqarcuy6/bot"
    headers = {
        "Content-Type": "application/json",
        "QISCUS_SDK_SECRET": "c7974edbd33f204f45e74b0f22c1ce15",
    }
    data = {
        "sender_email": "daki-fq9mhonubqarcuy6_admin@qismo.com",
        "message": message,
        "type": "text",
        "room_id": room_id,
    }
    requests.post(url, json=data, headers=headers)

def send_image_to_qiscus(room_id):
    image_url = "https://ragblobforspider.blob.core.windows.net/emache/mobile_app_coupon.png"
    url = "https://omnichannel.qiscus.com/daki-fq9mhonubqarcuy6/bot"
    headers = {
        "Content-Type": "application/json",
        "QISCUS_SDK_SECRET": "c7974edbd33f204f45e74b0f22c1ce15",
    }
    data = {
        "sender_email": "daki-fq9mhonubqarcuy6_admin@qismo.com",
        "message": "",
        "type": "file_attachment",
        "payload": {
            "url": image_url,
            "caption": "",
            "size": 0,
            "file_name": '',
            "pages": 1
        },
        "room_id": room_id,
    }
    requests.post(url, json=data, headers=headers) 