### Test google search
##CONSTANT
import os
import requests
import pandas as pd




class GoogleSearcher:
    def __init__(self,global_storage):
        self.knowledge_base = global_storage.knowledge_base
        
    
    def google_search(self, query):
        api_key = os.environ["GOOGLE_SEARCH_API_KEY"]
        cx = os.environ["GOOGLE_SEARCH_ENGINE_ID"]
        
        # Construct the URL
        url = f"https://www.googleapis.com/customsearch/v1?key={api_key}&cx={cx}&q={query}"
        
        response = requests.get(url)
        
        links = []
        
        if response.status_code == 200:
            data = response.json()
            for item in data.get("items", []):
                link = item.get("link")
                if link:
                    links.append(link)
            
            return links
        else:
            return None
        
    def forward(self, query):
        links = self.google_search(query)
        print(len(links))
        if len(links)!=0:
            all_matches_indexes = list(self.knowledge_base[self.knowledge_base['URL'].isin(links)].index)
            
            print('Google Search Results:')
            for index in all_matches_indexes:
                print(f"{index} : {self.knowledge_base.iloc[index]['Name']}")
            print('$'*20)
            context = ''
            for index in all_matches_indexes:
                sample = self.knowledge_base.iloc[index]
                context+=f"""
                <RETRIEVED_PACKAGE_{index})>
                <package_name>{sample.Name}</package_name>
                <package_url>{sample.URL}</package_url>
                <package_original_price>{sample['Original Price']}</package_original_price>
                <package_hdmall_price>{sample['HDmall Price']}</package_hdmall_price>
                <package_cash_discount>{sample['Cash Discount']}</package_cash_discount>
                <package_cash_price>{sample['Cash Price']}</package_cash_price>
                <package_reserve/deposit_price>{sample['Deposit Price']}</package_reserve/deposit_price>
                <package_price_details>{sample['Price Details']}</package_price_details>
                <package_booking_detail>{sample['Payment Booking Info']}</package_booking_detail>
                <full_or_starting_price?>{sample['Full or Starting Price']}</full_or_starting_price?>
                <installment_price_per_month>{sample['Installment Price']}</installment_price_per_month>
                <installment_months>{sample['Installment Month']}</installment_months>
                <hospital_or_shop_name>{sample['Shop Name']} {sample['Brand']}</hospital_or_shop_name>
                <selling_points>{sample['Preview 1-10']}{sample['Selling Point']}</selling_points>
                <min_or_max_age>{sample['Min/Max Age']}</min_or_max_age>
                <location>{sample['location']}</location>
                <package_information>{sample['Package Details']}{sample['Important Info']}{sample['General Info']}{sample['FAQ']}</package_information>
                </RETRIEVED_PACKAGE_{index})>
            """
        else :context=''
            
        return context
        
        
    
    



