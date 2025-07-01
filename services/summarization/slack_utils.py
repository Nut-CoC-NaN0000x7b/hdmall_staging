from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import os
from datetime import datetime, timedelta

def send_slack_message(channel, message, ts):
    """
    Send a message to a Slack channel.
    
    Args:
        channel (str): The channel name to send the message to (e.g., '#general')
        message (str): The message to send
        ts (str): Thread timestamp
    """
    # Initialize the Slack client with your bot token
    # You need to set SLACK_BOT_TOKEN environment variable
    client = WebClient(token=os.environ.get('SLACK_BOT_TOKEN'))
    
    try:
        # Send the message
        response = client.chat_postMessage(
            channel=channel,
            text=message,
            thread_ts=ts
        )
        print(f"Message sent successfully: {response['ts']}")
    except SlackApiError as e:
        print(f"Error sending message: {e.response['error']}")
    except Exception as e:
        print(f"Unexpected error sending slack message: {str(e)}") 