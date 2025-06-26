import requests

# Replace with the actual URL from your Cloud Function deployment
FUNCTION_URL = 'https://asia-southeast1-honestdocs-thailand-app.cloudfunctions.net/shortio-proxy'

def test_proxy():
    try:
        # Make POST request to your Cloud Function proxy
        response = requests.post(
            FUNCTION_URL,
            json={
                'originalURL': 'https://hdmall.co.th/highlight/allergy-test?openExternalBrowser=1&ai-id=hdmall-jibai'
            },
            headers={
                'Content-Type': 'application/json'
            }
        )
        
        # Check if request was successful
        response.raise_for_status()
        
        # The Cloud Function should return a JSON object with the short URL
        print('✅ Shortened URL:', response.json()['shortURL'])
        
    except requests.exceptions.RequestException as error:
        if hasattr(error, 'response'):
            print('❌ Error:', error.response.status_code, error.response.json())
        else:
            print('❌ Error:', str(error))

if __name__ == '__main__':
    test_proxy() 