# testing cartAPI feature

import requests
import subprocess
import json
#test token
#TOKEN = "4abc76154257d42db13e888a771b2dcc19203cd669ecb13a493415a6e7397c43d69a3d0098b3d4d992c4443b14229fd94db3deff3a34f4064d2d05dfe2a918ec"

#production token
TOKEN = "4783d3f405a1a83fce0558211bc97a6d7deb9cf5391ab4adc696e203583413aa274b13c1e8963da26a3f11be7e197ac75448b2c64c3f247a652e764dd17fa07a"
#TOKEN = "4783d3f405a1a83fce0558211bc97a6d7deb9cf5391ab4adc696e203583413aa274b13c1e8963da26a3f11be7e197ac75448b2c64c3f247a652e764dd17fa07a"
# creat cart
# curl -L -g -X POST 'http://localhost:3000/api/v3/carts?package_ids[]=46106&package_ids[]=18181' -H 'Authorization: Bearer <token>'


def create_cart_curl(chat_room_id):
    curl_command = [
        'curl',
        '-L',
        '-X', 'POST',
        'https://hdmall.co.th/api/v3/external_services/carts',
        #'http://staging.honestdocs.co/api/v3/external_services/carts',
        '-H', f'Authorization: Bearer {TOKEN}',
        '-H', 'Content-Type: application/json',
        '-d', json.dumps({'chat_room_id': chat_room_id})
    ]
    
    try:
        # Execute curl command and capture output
        result = subprocess.run(curl_command, capture_output=True, text=True)
        
        # Print the complete output for debugging
        print("Status:", result.returncode)
        print("Output:", result.stdout)
        
        # Try to parse JSON response if available
        if result.stdout:
            return json.loads(result.stdout)
        return None
    except Exception as e:
        print(f"Error executing curl command: {e}")
        return None


def add_package_to_cart(cart_id, package_url, chat_room_id):
    #speicla condition
    target = "https://hdmall.co.th/health-checkup/antigen-kit-for-covid19-atk-singclean-at-home-1-set-not-including-shipping-cosmy-co-ltd"
    if package_url == target or target in package_url or target.lower() in package_url.lower():
        return "This package is currently not available, OUT OF STOCK :("
    #########################################################
    curl_command = [    
        'curl',
        '-L',
        '-X', 'PUT',
        f'https://hdmall.co.th/api/v3/external_services/carts/{cart_id}',
        #f'http://staging.honestdocs.co/api/v3/external_services/carts/{cart_id}',
        '-H', f'Authorization: Bearer {TOKEN}',
        '-H', 'Content-Type: application/json',
        '-d', json.dumps({'package_url': package_url, 'chat_room_id': chat_room_id})
    ]

    try:
        result = subprocess.run(curl_command, capture_output=True, text=True)
        print("Status:", result.returncode)
        print("Output:", result.stdout)
        
        if result.stdout:
            return json.loads(result.stdout)
        return None
    except Exception as e:
        print(f"Error executing curl command: {e}")
        return None

def list_cart_packages_curl(cart_id, chat_room_id):
    #curl command : curl -X GET 'http://localhost:3000/api/v3/external_services/carts/3103?chat_room_id=123' -H 'Authorization: Bearer <token>'
    curl_command = [
        'curl',
        '-L',
        '-X', 'GET',
        f'https://hdmall.co.th/api/v3/external_services/carts/{cart_id}',
        #f'http://staging.honestdocs.co/api/v3/external_services/carts/{cart_id}',
        '-H', f'Authorization: Bearer {TOKEN}',
        '-H', 'Content-Type: application/json',
        '-d', json.dumps({'chat_room_id': chat_room_id})
    ]
    try:
        result = subprocess.run(curl_command, capture_output=True, text=True)
        print("Status:", result.returncode)
        #print("Output:", result.stdout)
        
        if result.stdout:
            return json.loads(result.stdout)
        return None
    except Exception as e:
        print(f"Error executing curl command: {e}")
        return None


def delete_cart_curl(cart_id, chat_room_id):
    #example curl command : curl -X DELETE 'http://localhost:3000/api/v3/external_services/carts/3094?chat_room_id=123' -H 'Authorization: Bearer <token>'
    curl_command = [
        'curl',
        '-L',
        '-X', 'DELETE',
        f'https://hdmall.co.th/api/v3/external_services/carts/{cart_id}?chat_room_id={chat_room_id}',
        #f'http://staging.honestdocs.co/api/v3/external_services/carts/{cart_id}?chat_room_id={chat_room_id}',
        '-H', f'Authorization: Bearer {TOKEN}',
    ]
    try:
        result = subprocess.run(curl_command, capture_output=True, text=True)
        print("Status:", result.returncode)
        print("Output:", result.stdout)
        if result.stdout:
            return json.loads(result.stdout)
        return None
    except Exception as e:
        print(f"Error executing curl command: {e}")
        return None

def create_order_curl(cart_id, chat_room_id):
    #curl -X POST 'http://localhost:3000/api/v3/external_services/orders/new?cart_id=3049' -H 'Authorization: Bearer <token>'
    curl_command = [
        'curl',
        '-L',
        '-X', 'GET',
        f'https://hdmall.co.th/api/v3/external_services/orders/new?cart_id={cart_id}&chat_room_id={chat_room_id}',
        #f'http://staging.honestdocs.co/api/v3/external_services/orders/new?cart_id={cart_id}&chat_room_id={chat_room_id}',
        '-H', f'Authorization: Bearer {TOKEN}',
    ]
    print(curl_command)
    try:
        result = subprocess.run(curl_command, capture_output=True, text=True)
        print("Status:", result.returncode)
        print("Output:", result.stdout)
        if result.stdout:
            return json.loads(result.stdout)
        return None
    except Exception as e:
        print(f"Error executing curl command: {e}")
        return None
    
def delete_package_curl(package_url, chat_room_id, cart_id):
    #curl -X DELETE 'http://localhost:3000/api/v3/external_services/carts/3049/packages/male-cancer-checkup?chat_room_id=123' --header 'Authorization: Bearer <token>'
    curl_command = [
        'curl',
        '-L',
        '-X', 'DELETE',
        f'https://hdmall.co.th/api/v3/external_services/carts/{cart_id}/packages/{package_url}?chat_room_id={chat_room_id}',
        #f'http://staging.honestdocs.co/api/v3/external_services/carts/{cart_id}/packages/{package_url}?chat_room_id={chat_room_id}',
        '-H', f'Authorization: Bearer {TOKEN}',
    ]
    try:
        result = subprocess.run(curl_command, capture_output=True, text=True)
        print("Status:", result.returncode)
        print("Output:", result.stdout)
        if result.stdout:
            return json.loads(result.stdout)
        return None
    except Exception as e:
        print(f"Error executing curl command: {e}")
        return None
    

#chat_room_id = 264062881
#cart_id = 1892
#list_packages = list_cart_packages_curl(cart_id, chat_room_id)
#print(list_packages)
#package_url_1 = "course-laser-hair-removal-armpit-12-times-yag-laser-hdmall-plus-the-cover-clinic"
#delete_package_curl(package_url_1, chat_room_id, cart_id)
#create cart
#result = create_cart_curl("264062881")
#print(result['id'])
#cart_id = result['id']
#add package to cart
#add_package_to_cart(cart_id, package_url_1, chat_room_id)
#list packages in cart
#list_packages = list_cart_packages_curl(1974, "274619704")
#print(list_packages)
#create order
#create_order_curl(1892, chat_room_id)
#room_id = "112355437"
#result = list_cart_packages_curl(39142, room_id)
#print(result)
#order = create_order_curl(result['data']['id'], room_id)
#print(order)