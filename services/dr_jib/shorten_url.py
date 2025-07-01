import requests

# 🔐 Replace with your actual values
SHORT_IO_API_KEY = 'sk_2VDS1P2F09VaXJPv'
SHORT_IO_DOMAIN = 's.hdmall.co.th'  # e.g., 'hdcare.short.gy'
ORIGINAL_URL = 'https://hdmall.co.th/c/reward?openExternalBrowser=1&ai-id=hdmall-jibai'

def shorten_url(original_url):
    try:
        response = requests.post(
            'https://api.short.io/links',
            json={
                'domain': SHORT_IO_DOMAIN,
                'originalURL': original_url
            },
            headers={
                'Content-Type': 'application/json',
                'Authorization': SHORT_IO_API_KEY
            }
        )
        
        # Check if request was successful
        response.raise_for_status()
        
        print('✅ Shortened URL:', response.json()['shortURL'])
        
    except requests.exceptions.RequestException as error:
        if hasattr(error, 'response'):
            print('❌ API Error:', error.response.status_code, error.response.json())
        else:
            print('❌ Error:', str(error))

if __name__ == '__main__':
    shorten_url(ORIGINAL_URL) 