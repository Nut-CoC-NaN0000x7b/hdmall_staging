from .bm25_searcher import BM25Retriever
from .semantic_searcher import SemanticRetriever
from .rank_fusion import compute_rrf, get_top_k
from .reranker import Reranker
from dotenv import load_dotenv
import os
import pandas as pd
import re
import httpx
import base64
import requests
import urllib.parse
#geo dist
import geopy.distance
import numpy as np
import asyncio
from functools import lru_cache
import aiohttp
from typing import Optional, Tuple
import logging
import json




#CONSTANT
load_dotenv()
api_key = os.getenv('ANTHROPIC_CLAUDE_API_KEY')

access_token = os.getenv('AIRTABLE_API_KEY')
base_id = os.getenv('AIRTABLE_BASE_ID')
table_id = os.getenv('AIRTABLE_TABLE_ID')
geocode_api = os.getenv('GEOCODE_API')







#hl mapping loading
# Get the directory of this file and navigate to hl_prompts
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
hl_mapping_path = os.path.join(project_root, "hl_prompts", "hl_mapping.json")

with open(hl_mapping_path, "r") as f:
    loaded_list = json.load(f)

logger = logging.getLogger(__name__)

class RAG:
    def __init__(self, global_storage):
        self.global_storage = global_storage
        self.knowledge_base = global_storage.knowledge_base
        
        print(f"RAG : {self.knowledge_base.shape}")
        print(f"RAG : {self.knowledge_base.columns[0]}")
        
        # Initialize core components
        self.lexical_searcher = BM25Retriever(tokens_file=self.global_storage.doc_json)
        self.semantic_searcher = SemanticRetriever(self.global_storage.embed_matrix)
        
        self.embed_type = 'name'
        self.hl_map = loaded_list
        
        #for plus
        self.semantic_searcher_plus = SemanticRetriever(self.global_storage.embed_matrix_plus)
        self.lexical_searcher_plus = BM25Retriever(tokens_file=self.global_storage.doc_json_plus)
        #index list for last fetch
        self.index_list = global_storage.index_list
        self.index_list_plus = global_storage.index_list_plus
        
        #for web recommendation
        self.web_recommendation_json = global_storage.web_recommendation_json
        self.semantic_searcher_hl = SemanticRetriever(global_storage.hl_embed)
        self.semantic_searcher_brand = SemanticRetriever(global_storage.brand_embed)
        self.semantic_searcher_cat = SemanticRetriever(global_storage.cat_embed)
        self.semantic_searcher_tag = SemanticRetriever(global_storage.tag_embed)

        self.lexical_searcher_hl = BM25Retriever(tokens_file=global_storage.hl_docs)
        self.lexical_searcher_brand = BM25Retriever(tokens_file=global_storage.brand_docs)
        self.lexical_searcher_cat = BM25Retriever(tokens_file=global_storage.cat_docs)
        self.lexical_searcher_tag = BM25Retriever(tokens_file=global_storage.tag_docs)
        
        # Add connection session for HTTP requests
        self._session: Optional[aiohttp.ClientSession] = None
        
        # Cache for geocoding results (LRU cache with max 1000 entries)
        self._geocode_cache = {}

    def _truncate_text(self, text: str, max_length: int = 100) -> str:
        """Helper method to truncate long text for logging purposes"""
        if len(text) <= max_length:
            return text
        return text[:max_length] + "..." + f" ({len(text)} chars total)"

    def normalize_brand_name(self, brand_query: str) -> str:
        """
        Normalize common brand abbreviations and variations to full brand names.
        This helps with exact matching in database queries.
        """
        if not brand_query:
            return brand_query
            
        # Convert to lowercase for case-insensitive matching
        brand_lower = brand_query.lower().strip()
        
        # Brand mappings - add more as needed
        brand_mappings = {
            'baac': 'Bangkok Anti Aging Center',
            'bangkok anti aging': 'Bangkok Anti Aging Center',
            'bkk anti aging': 'Bangkok Anti Aging Center',
            
            # Add more common abbreviations here
            'bh': 'Bangkok Hospital',
            'bangkok hosp': 'Bangkok Hospital',
            
            'samitivej': 'โรงพยาบาลสมิติเวช',
            'bumrungrad': 'โรงพยาบาลบำรุงราด',
            'siriraj': 'โรงพยาบาลศิริราช',
            
            # Kasemrad variations
            'เกษมราษฎร์': 'โรงพยาบาลเกษมราษฎร์',
            'kasemrad': 'โรงพยาบาลเกษมราษฎร์',
            
            # Add more mappings as you discover common user patterns
        }
        
        # Check for exact matches first
        if brand_lower in brand_mappings:
            return brand_mappings[brand_lower]
            
        # Check for partial matches (if brand_query contains the key)
        for abbrev, full_name in brand_mappings.items():
            if abbrev in brand_lower:
                return full_name
                
        # If no match found, return original
        return brand_query

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session with connection pooling"""
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(
                limit=100,  # Total connection pool size
                limit_per_host=30,  # Max connections per host
                ttl_dns_cache=300,  # DNS cache TTL
                use_dns_cache=True,
            )
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout
            )
        return self._session
    
    async def close_session(self):
        """Close the aiohttp session"""
        if self._session and not self._session.closed:
            await self._session.close()

    def _image_context_generator(self, image_urls):
        image_context = []
        image_context.append({"type":"text", "text":"<image_context>"})

        for index, _url in enumerate(image_urls):
            image_url = _url['image_url']
            image_data = base64.standard_b64encode(httpx.get(image_url).content).decode("utf-8")
            image_context.append({"type":"image","source":{"type": "base64","media_type": 'image/png',"data": image_data,}})
            image_context.append({"type":"text", "text":f"<image_index={index}><image_url>{image_url}</image_url></image_index={index}>"})

        image_context.append({"type":"text","text":"</images_context>"})
        image_context_block = [{"role":"user", "content":image_context}]

        return image_context_block
    
    def _get_infographic_urls(self, category_tag:str):
        #find hl_url from hl_map
        hl_url = None
        for d in self.hl_map:
            if d['cat_name'].strip() in category_tag.strip() or category_tag.strip() in d['cat_name'].strip():
                hl_url = d['hl_url']
                break
        print(f"hl_url : {hl_url}")
        headers = {
            "Authorization": f"Bearer {access_token}"
        }

        params = {
            "filterByFormula": f'{{hl_url}}="{hl_url}"'
        }

        url = f'https://api.airtable.com/v0/app2CSihSxsRF1acK/tblNy0vqAW3FApPxU'

        try:
            res = requests.get(url=url, headers=headers, params=params)
            data = res.json()

            print(f"data : {data}")


            records = data.get('records')

            if len(records) == 0:
                # No infographics
                #logger.info(f"No infographics for package : {package_url}")
                return None

            artworks = records[0].get('fields').get('Artwork')
            #package_name = records[0].get('fields').get('Package Name')
            #package_name = package_name.split(' - SKU')[0]
            

            res = []
            for artwork in artworks:
                res.append({'image_url':artwork.get('url')})

            #logger.info(f"Inf graphics for package : {package_url} : {res}")
            return res
        except Exception as e:
            print(f"Something went wrong when trying to fetch infographics : {e}")
            return None
        

    def _initialize_components(self):
        if self.lexical_searcher is None:
            self.lexical_searcher = BM25Retriever(tokens_file=self.global_storage.doc_json)
        if self.semantic_searcher is None:
            self.semantic_searcher = SemanticRetriever(self.global_storage.embed_matrix)
        if self.knowledge_base is None:
            self.knowledge_base = self.global_storage.knowledge_base
        
    def _remove_duplicates(self,image_list):
        seen_urls = set()
        unique_images = []
        for image in image_list:
            if image['image_url'] not in seen_urls:
                seen_urls.add(image['image_url'])
                unique_images.append(image)
        return unique_images

    @lru_cache(maxsize=1000)
    def _get_geocode_cached(self, input_string: str, api_key: str = geocode_api) -> Tuple[Optional[float], Optional[float]]:
        """Cached version of geocoding to avoid repeated API calls"""
        if input_string in self._geocode_cache:
            return self._geocode_cache[input_string]
            
        base_url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            "address": input_string,
            "key": api_key
        }

        url = f"{base_url}?{urllib.parse.urlencode(params)}"
        response = requests.get(url, timeout=10)  # Add timeout
        data = response.json()

        if data.get("status") == "OK":
            results = data.get("results", [])
            if results:
                location = results[0]["geometry"]["location"]
                lat = location["lat"]
                lng = location["lng"]
                result = (lat, lng)
                self._geocode_cache[input_string] = result
                return result
            else:
                print("No location found for that address")
                result = (None, None)
                self._geocode_cache[input_string] = result
                return result
        else:
            result = (None, None)
            self._geocode_cache[input_string] = result
            return result

    def _get_geocode(self, input_string, api_key = geocode_api):
        """Wrapper for the cached geocoding function"""
        return self._get_geocode_cached(input_string, api_key)
    
    def _get_geo_distance(self, coor1, coor2):
        return float(geopy.distance.geodesic(coor1, coor2).km)


    
    def _get_geo_mask(self, area:str, indexes_list, dist_threshold):
        m = len(indexes_list)
        ones_mask = np.array([1 for _ in range(m)])
        
        # Return all ones if area is unknown or empty
        if not area or area == "<UNKNOWN>":
            return ones_mask
    
        lat, lng = self._get_geocode(area)
        print(lat, lng)
        if lat and lng:
            mask = []
            for i in range(m):
                try:
                    _coor = indexes_list[i]['coor']
                    coor1 = (float(_coor[0]), float(_coor[1]))
                    coor2 = (float(lat), float(lng))
                    dist = float(self._get_geo_distance(coor1, coor2))
                    if dist <= dist_threshold:
                        mask.append(1)
                    else:
                        mask.append(0)
                except:
                    # If there's any error processing coordinates, include the item
                    mask.append(1)
            
            # If mask is all zeros, return ones_mask instead
            mask_array = np.array(mask)
            return mask_array if mask_array.sum() > 0 else ones_mask
        
        return ones_mask





    def _get_hl_mask(self, category_tag:str):
        package_urls = []
        # Search through hl_map for matching category
        for d in self.hl_map:
            #print(d['cat_name'], category_tag)
            if d['cat_name'] == category_tag:
                package_urls = d['packages']
                break  # Exit loop once found
        
        m = len(self.index_list)
        # If we found matching packages, create mask based on them
        if len(package_urls) > 0:
            mask = []
            for i in range(m):
                if self.index_list[i]['package_url'] in package_urls:
                    mask.append(1)
                else:
                    mask.append(0)
            return np.array(mask)
        else:
            # Return all ones if no matching category or packages found
            return np.array([1 for _ in range(m)])


    
    def forward(self,query: str, preferred_area: str, radius: int, category_tag:str) -> str:
        DEFAULT_RADIUS_THRESHOLD = 15 # in Km
        K = 150
        N = 10
        try:
            radius = int(radius)
        except:
            radius = DEFAULT_RADIUS_THRESHOLD
        self._initialize_components()
        geo_mask = self._get_geo_mask(preferred_area, self.index_list, radius)
        print(geo_mask)
        print(sum(geo_mask))
        hl_mask = self._get_hl_mask(category_tag)
        print(hl_mask)
        print(sum(hl_mask))
        
        # Apply both masks and then calculate the combined length
        combined_mask = geo_mask * hl_mask
        combined_mask_len = sum(combined_mask)
        print(combined_mask)
        print(combined_mask_len)
        if combined_mask_len == 0:
            print("****filters too much, apply only hl_mask****")
            combined_mask = hl_mask
            combined_mask_len = sum(combined_mask)

        lexical_dict = self.lexical_searcher.forward(query)
        semantic_dict = self.semantic_searcher.forward(query)
        dict_rrf_score = compute_rrf(lexical_dict, semantic_dict, mask=combined_mask)
        one_mask = np.array([1 for _ in range(len(self.index_list))])
        dict_rrf_score_non_filtered = compute_rrf(lexical_dict, semantic_dict, mask=one_mask)
        

        #lower bound based on combined mask
        if combined_mask_len < K:
            K = int(combined_mask_len)
            if combined_mask_len < N:
                N = int(combined_mask_len)

        dict_top_k = get_top_k(dict_rrf_score, k=K)
        dict_top_k_non_filtered = get_top_k(dict_rrf_score_non_filtered, k=20)
        top_k_indexes = [int(idx) for idx in dict_top_k.keys()]
        top_k_indexes_non_filtered = [int(idx) for idx in dict_top_k_non_filtered.keys()]
        reranker = Reranker(top_k_indexes, self.knowledge_base,self.index_list) 
        reranker_non_filtered = Reranker(top_k_indexes_non_filtered, self.knowledge_base,self.index_list)
        print(N, K)
        #print its type too
        print(type(N), type(K))
        rerank_top_k = reranker.forward(query, top_n=N)
        rerank_top_k_non_filtered = reranker_non_filtered.forward(query, top_n=10)
        
        #top_p_index = list(set([self.index_list[ind]['index'] for ind in rerank_top_k]))
            

        
        print(f'RAG retrieval results W/FILTER, type:{self.embed_type}:')
        for index in rerank_top_k:
            true_index = self.index_list[index]['index']
            truncated_text = self._truncate_text(self.index_list[index]['text'])
            print(f"Local/Global Index : {index} : {true_index} \n {truncated_text}")
        print('$'*20)

        print(f'RAG retrieval results NO-FILTERED, type:{self.embed_type}:')
        for index in rerank_top_k_non_filtered:
            true_index = self.index_list[index]['index']
            truncated_text = self._truncate_text(self.index_list[index]['text'])
            print(f"Local/Global Index : {index} : {true_index} \n {truncated_text}")
        print('$'*20)

        
        context = ''
        for index in rerank_top_k:
            clinic_sample = self.index_list[index]
            #clinic_sample has index, text, address, coor, map_url
            true_index = clinic_sample['index']
            sample = self.knowledge_base.iloc[true_index]
            context+=f"""
            <RETRIEVED_PACKAGE_{true_index}>
            <package_name>{clinic_sample['text']}</package_name>
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
            <location_information> Address : {clinic_sample['address']} \n Google Map : {clinic_sample['map_url']}</location_information>
            <package_information>{sample['Package Details']}{sample['Important Info']}{sample['General Info']}{sample['FAQ']}</package_information>
            </RETRIEVED_PACKAGE_{index}>
            """
    
        #non filtered
        context_non_filtered = ''
        for index in rerank_top_k_non_filtered:
            clinic_sample = self.index_list[index]
            true_index = clinic_sample['index']
            sample = self.knowledge_base.iloc[true_index]
            context_non_filtered+=f"""
            <RETRIEVED_PACKAGE_{true_index}>
            <package_name>{clinic_sample['text']}</package_name>
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
            <location_information> Address : {clinic_sample['address']} \n Google Map : {clinic_sample['map_url']}</location_information>
            <package_information>{sample['Package Details']}{sample['Important Info']}{sample['General Info']}{sample['FAQ']}</package_information>
            </RETRIEVED_PACKAGE_{true_index}>
            """

        

        img_url_resp = self._get_infographic_urls(category_tag)
        #truncate with top 5 
        if img_url_resp:
            if len(img_url_resp) > 5:
                image_context = self._image_context_generator(img_url_resp[:5])
            else:
                image_context = self._image_context_generator(img_url_resp)
        else:
            image_context = [{"role":"user", "content":"<IMAGE_CONTEXT>No infographics</IMAGE_CONTEXT>"}]
            
        
        
        text_context = context
        text_context_non_filtered = context_non_filtered
        return text_context,text_context_non_filtered,image_context
        
        


    def get_images(self, package_urls):
        # Get infographics based on package_urls parsed from haiku <json>
        # return
        #------
        #image/text messages object, [{},{},{}], can be added to other messages
        out = self._image_context_generator(package_urls)
        return out
    def _get_package_url(self,query: str, preferred_area: str, radius: int, category_tag:str):
        self._initialize_components()
        
        # Extract and normalize brand if present in query
        normalized_query = query
        # Simple brand extraction - look for common brand patterns
        for brand_abbrev in ['baac', 'bh', 'bangkok anti aging', 'samitivej', 'bumrungrad', 'siriraj', 'เกษมราษฎร์', 'kasemrad']:
            if brand_abbrev.lower() in query.lower():
                original_brand = brand_abbrev
                normalized_brand = self.normalize_brand_name(brand_abbrev)
                if normalized_brand != original_brand:
                    normalized_query = normalized_query.replace(original_brand, normalized_brand)
                    print(f"Search query brand normalization: '{original_brand}' → '{normalized_brand}'")
                break
        DEFAULT_RADIUS_THRESHOLD = 10
        area = preferred_area
        K = 15
        N = 5
        try:
            radius = int(radius)
        except:
            radius = DEFAULT_RADIUS_THRESHOLD
        self._initialize_components()
        geo_mask = self._get_geo_mask(area, self.index_list, radius)
        print(f"geo_mask: {sum(geo_mask)} items")
        hl_mask = self._get_hl_mask(category_tag)
        print(f"hl_mask: {sum(hl_mask)} items")
        # Apply both masks and then calculate the combined length
        combined_mask = geo_mask * hl_mask
        combined_mask_len = sum(combined_mask)
        print(f"combined_mask: {combined_mask_len} items")
        if combined_mask_len == 0:
            print("****filters too much, apply only hl_mask****")
            combined_mask = hl_mask
            combined_mask_len = sum(combined_mask)

        lexical_dict = self.lexical_searcher.forward(normalized_query)
        semantic_dict = self.semantic_searcher.forward(normalized_query)
        dict_rrf_score = compute_rrf(lexical_dict, semantic_dict, mask=combined_mask)
        one_mask = np.array([1 for _ in range(len(self.index_list))])
        dict_rrf_score_non_filtered = compute_rrf(lexical_dict, semantic_dict, mask=one_mask)

        #lower bound based on combined mask
        if combined_mask_len < K:
            K = int(combined_mask_len)
            if combined_mask_len < N:
                N = int(combined_mask_len)

        dict_top_k = get_top_k(dict_rrf_score, k=K)
        dict_top_k_non_filtered = get_top_k(dict_rrf_score_non_filtered, k=150)
        top_k_indexes = [int(idx) for idx in dict_top_k.keys()]
        top_k_indexes_non_filtered = [int(idx) for idx in dict_top_k_non_filtered.keys()]
        reranker = Reranker(top_k_indexes, self.knowledge_base,self.index_list) 
        reranker_non_filtered = Reranker(top_k_indexes_non_filtered, self.knowledge_base,self.index_list)
        print(N, K)
        #print its type too
        print(type(N), type(K))
        rerank_top_k = reranker.forward(normalized_query, top_n=N)
        rerank_top_k_non_filtered = reranker_non_filtered.forward(normalized_query, top_n=2)

        print(f'RAG retrieval results W/FILTER, type:{self.embed_type}:')
        for index in rerank_top_k:
            true_index = self.index_list[index]['index']
            truncated_text = self._truncate_text(self.index_list[index]['text'])
            print(f"Local/Global Index : {index} : {true_index} \n {truncated_text}")
        print('$'*20)

        print(f'RAG retrieval results NO-FILTERED, type:{self.embed_type}:')
        for index in rerank_top_k_non_filtered:
            true_index = self.index_list[index]['index']
            truncated_text = self._truncate_text(self.index_list[index]['text'])
            print(f"Local/Global Index : {index} : {true_index} \n {truncated_text}")
        print('$'*20)

        context = ''
        context_non_filtered = ''
        for index in rerank_top_k:
            clinic_sample = self.index_list[index]
            true_index = clinic_sample['index']
            sample = self.knowledge_base.iloc[true_index]
            context+=f"""
            <RETRIEVED_PACKAGE_{true_index} type=highlights>
            <package_name>{clinic_sample['text']}</package_name>
            <package_url>{sample.URL}</package_url>
            <package_original_price>{sample['Original Price']}</package_original_price>
            <package_hdmall_price>{sample['HDmall Price']}</package_hdmall_price>
            <package_cash_discount>{sample['Cash Discount']}</package_cash_discount>
            <package_cash_price>{sample['Cash Price']}</package_cash_price>
            <package_reserve/deposit_price>{sample['Deposit Price']}</package_reserve/deposit_price>
            <full_or_starting_price?>{sample['Full or Starting Price']}</full_or_starting_price?>
            </RETRIEVED_PACKAGE_{true_index}>
            """

        for index in rerank_top_k_non_filtered:
            clinic_sample = self.index_list[index]
            true_index = clinic_sample['index']
            sample = self.knowledge_base.iloc[true_index]
            context_non_filtered+=f"""
            <RETRIEVED_PACKAGE_{true_index} type=normal>
            <package_name>{clinic_sample['text']}</package_name>
            <package_url>{sample.URL}</package_url>
            <package_original_price>{sample['Original Price']}</package_original_price>
            <package_hdmall_price>{sample['HDmall Price']}</package_hdmall_price>
            <package_cash_discount>{sample['Cash Discount']}</package_cash_discount>
            <package_cash_price>{sample['Cash Price']}</package_cash_price>
            <package_reserve/deposit_price>{sample['Deposit Price']}</package_reserve/deposit_price>
            <full_or_starting_price?>{sample['Full or Starting Price']}</full_or_starting_price?>
            </RETRIEVED_PACKAGE_{true_index}>
            """
        text_context = context+context_non_filtered

        #TODO : fix this
        #img_urls = self._get_infographic_urls(category_tag)
        content_block = [{
            "type":"text",
            "text":text_context
        }]
        #if img_urls:
        #    for url in img_urls:
        #        image_url = url['image_url']

        #        image_data = base64.standard_b64encode(httpx.get(image_url).content).decode("utf-8")
        #        content_block.append(
        #            {"type":"image", "source":{"type": "base64","media_type": 'image/png',"data": image_data,}}
        #            )
        #    content_block.append(
        #        {"type":"text", "text":f"<image_url>{image_url}</image_url>"}
        #        )
        return content_block
        
    
    def get_package_info_from_url(self, package_url: str):
        self._initialize_components()
        out = self.knowledge_base[self.knowledge_base['URL'] == package_url]
        if out.empty:
            return "no package found, please check your package_url again"
        
        # Get the first (and should be only) matching row
        row = out.iloc[0]
        
        context = f"""
        <PACKAGE_INFO>
        <package_name>{row['Name']}</package_name>
        <package_url>{row['URL']}</package_url>
        <package_information>{row['Package Details']}{row['Important Info']}{row['General Info']}{row['FAQ']}</package_information>
        <package_original_price>{row['Original Price']}</package_original_price>
        <package_hdmall_price>{row['HDmall Price']}</package_hdmall_price>
        <package_cash_discount>{row['Cash Discount']}</package_cash_discount>
        <package_cash_price>{row['Cash Price']}</package_cash_price>
        <package_reserve/deposit_price>{row['Deposit Price']}</package_reserve/deposit_price>
        <package_price_details>{row['Price Details']}</package_price_details>
        <package_booking_detail>{row['Payment Booking Info']}</package_booking_detail>
        <full_or_starting_price?>{row['Full or Starting Price']}</full_or_starting_price?>
        <installment_price_per_month>{row['Installment Price']}</installment_price_per_month>
        <installment_months>{row['Installment Month']}</installment_months>
        <hospital_or_shop_name>{row['Shop Name']} {row['Brand']}</hospital_or_shop_name>
        <selling_points>{row['Preview 1-10']}{row['Selling Point']}</selling_points>
        <min_or_max_age>{row['Min/Max Age']}</min_or_max_age>
        <location_information> Address : {row['location']}</location_information>
        </PACKAGE_INFO>
        """
        return context




    def search_for_web(self,query: str):
        #make one mask 
        one_mask = np.array([1 for _ in range(len(self.index_list))])


        lexical_dict = self.lexical_searcher.forward(query)
        semantic_dict = self.semantic_searcher.forward(query)
        dict_rrf_score = compute_rrf(lexical_dict, semantic_dict, mask=one_mask)
        #get keys of dict_rrf_score
        idx_list = list(dict_rrf_score.keys())
        true_index_list = list(set([self.index_list[index]['index'] for index in idx_list[:100]]))
        print(f"idx_list BEFORE: {len(true_index_list)} items")
        brand_rank_list = []
        for index in true_index_list:
            brand_rank = self.knowledge_base.iloc[index]['Brand Ranking (Position)']
            brand_rank_list.append((brand_rank, index))
        brand_rank_list = sorted(brand_rank_list, key=lambda x: x[0])
        print(f"brand_rank_list: {len(brand_rank_list)} items sorted by rank")
        true_index_list = [x[1] for x in brand_rank_list]
        print(f"idx_list AFTER: {len(true_index_list)} items")


        package_list = []
        highlight_name_list = []
        brands = []
        for true_index in true_index_list:
            sample = self.knowledge_base.iloc[true_index]
            sample = self.knowledge_base.iloc[true_index]
            ###
            type = 'package'
            package_name = sample['Name']
            package_url = sample['URL']
            brand_name = sample['Brand']
            category = sample['Category']
            p3_price = sample['HDmall Price']
            cash_price = sample['Cash Price']
            brand_rank = sample['Brand Ranking (Position)']
            brand_url = f'https://hdmall.co.th/{brand_name.lower().replace('&', '').replace(' ', '-')}'
            if brand_url == "https://hdmall.co.th/stc-anti-aging--wellness-clinic":
                brand_url = "https://hdmall.co.th/stc-anti-aging-wellness-clinic"
            brands.append({
                'brand_name':brand_name,
                'brand_url':brand_url,
                'brand_rank':int(brand_rank)
            })
            for d in self.hl_map:
                if category == d['cat_name']:
                    highlight_name_list.append(d['cat_name'])
                    break
            package_list.append({
                'type':type,
                'package_name':package_name,
                'package_url':package_url,
                'brand_name':brand_name,
                'p3_price':p3_price,
                'cash_price':cash_price,
                'brand_rank':str(brand_rank)
            })

        #remove duplicates in highlight_name_list
        highlight_name_list = list(set(highlight_name_list))
        highlight_list = []
        for hl_name in highlight_name_list:
            for d in self.hl_map:
                if hl_name == d['cat_name']:
                    highlight_list.append({
                        'hl_name':hl_name,
                        'hl_url':d['hl_url']
                    })
                    break
        result = {
            'search_query':query,
            'search_result':{
                'packages': package_list,
                'highlights':highlight_list,
                'brands':[]
            }
        }
        #remove duplicates by brand_name and sort by rank
        unique_brands = {}
        for brand in brands:
            brand_name = brand['brand_name']
            if brand_name not in unique_brands or brand['brand_rank'] < unique_brands[brand_name]['brand_rank']:
                unique_brands[brand_name] = brand
        
        # Convert back to list and sort by rank
        sorted_brands = sorted(unique_brands.values(), key=lambda x: x['brand_rank'])
        
        result['search_result']['brands'] = sorted_brands

        #print with nice indent - truncated
        print(f"Search result: {len(result['search_result']['packages'])} packages, {len(result['search_result']['highlights'])} highlights, {len(result['search_result']['brands'])} brands")
        return result
        
    


    def ads_forward(self,input_block: dict) -> str:

        search_query = input_block['search_query']
        location = input_block['location']
        category_tag = input_block['category_tag']
        radius = 7 # in Km
        K = 150
        N = 10

        self._initialize_components()
        geo_mask = self._get_geo_mask(location, self.index_list, radius)
        print(f"geo_mask: {sum(geo_mask)} items")
        hl_mask = self._get_hl_mask(category_tag)
        print(f"hl_mask: {sum(hl_mask)} items")
        
        # Apply both masks and then calculate the combined length
        combined_mask = geo_mask * hl_mask
        combined_mask_len = sum(combined_mask)
        print(f"combined_mask: {combined_mask_len} items")
        if combined_mask_len == 0:
            print("****filters too much, apply only hl_mask****")
            combined_mask = hl_mask
            combined_mask_len = sum(combined_mask)

        lexical_dict = self.lexical_searcher.forward(search_query)
        semantic_dict = self.semantic_searcher.forward(search_query)
        dict_rrf_score = compute_rrf(lexical_dict, semantic_dict, mask=combined_mask)
        one_mask = np.array([1 for _ in range(len(self.index_list))])
        dict_rrf_score_non_filtered = compute_rrf(lexical_dict, semantic_dict, mask=one_mask)
        
        #lower bound based on combined mask
        if combined_mask_len < K:
            K = int(combined_mask_len)
            if combined_mask_len < N:
                N = int(combined_mask_len)

        dict_top_k = get_top_k(dict_rrf_score, k=K)
        dict_top_k_non_filtered = get_top_k(dict_rrf_score_non_filtered, k=150)
        top_k_indexes = [int(idx) for idx in dict_top_k.keys()]
        top_k_indexes_non_filtered = [int(idx) for idx in dict_top_k_non_filtered.keys()]
        reranker = Reranker(top_k_indexes, self.knowledge_base,self.index_list) 
        reranker_non_filtered = Reranker(top_k_indexes_non_filtered, self.knowledge_base,self.index_list)
        print(N, K)
        #print its type too
        print(type(N), type(K))
        rerank_top_k = reranker.forward(search_query, top_n=N)
        rerank_top_k_non_filtered = reranker_non_filtered.forward(search_query, top_n=10)
        
        # Convert local indices to true indices first
        filtered_true_indices = [self.index_list[idx]['index'] for idx in rerank_top_k]
        non_filtered_true_indices = [self.index_list[idx]['index'] for idx in rerank_top_k_non_filtered]
        
        # Take top 3 from filtered results
        top_3_filtered = filtered_true_indices[:3]
        
        # Take top 2 from non-filtered results, avoiding duplicates
        top_2_non_filtered = []
        for true_idx in non_filtered_true_indices:
            if true_idx not in top_3_filtered and len(top_2_non_filtered) < 2:
                top_2_non_filtered.append(true_idx)
        
        # Combine the results
        final_true_indices = top_3_filtered + top_2_non_filtered
        

        
        print(f'RAG retrieval results for ADS (top 5):')
        for index in final_true_indices:
            package_name = self.knowledge_base.iloc[index]['Name']
            truncated_name = self._truncate_text(package_name)
            print(f"Global Index : {index} \n {truncated_name}")
        print('$'*20)

        contextual_ads_block = []
        for index in final_true_indices:
            sample = self.knowledge_base.iloc[index]
            name = sample['Name']
            image = sample['Package Picture']
            url = sample['URL']
            cash_price = sample['Cash Price']
            context_block = {
                "product_name":name,
                "product_url":url,
                "product_image_url":image,
                "product_cash_price":cash_price
            }

            print(f"context_block : {context_block['product_name'][:50]}... (URL: {context_block['product_url']})")
            contextual_ads_block.append(context_block)

            
        
        return contextual_ads_block
    

    def web_recommendation(self, query: str, type: str):
        print(f"web_recommendation. . . : {type}")
        
        # Normalize brand names for brand searches
        normalized_query = query
        if type == 'brand':
            normalized_query = self.normalize_brand_name(query)
            if normalized_query != query:
                print(f"Brand search normalization: '{query}' → '{normalized_query}'")
        
        if type == 'hl':
            semantic_engine = self.semantic_searcher_hl
            lexical_engine = self.lexical_searcher_hl
            knowledge = self.web_recommendation_json['highlights_data']
            one_mask = np.array([1 for _ in range(len(knowledge))])
        elif type == 'brand':
            semantic_engine = self.semantic_searcher_brand
            lexical_engine = self.lexical_searcher_brand
            knowledge = self.web_recommendation_json['brand_data']
            one_mask = np.array([1 for _ in range(len(knowledge))])
        elif type == 'cat':
            semantic_engine = self.semantic_searcher_cat
            lexical_engine = self.lexical_searcher_cat
            knowledge = self.web_recommendation_json['category_data']
            one_mask = np.array([1 for _ in range(len(knowledge))])
        elif type == 'tag':
            semantic_engine = self.semantic_searcher_tag
            lexical_engine = self.lexical_searcher_tag
            knowledge = self.web_recommendation_json['tags_data']
            one_mask = np.array([1 for _ in range(len(knowledge))])

        
        #text with cohere embeddings

        semantic_dict = semantic_engine.forward_cohere(normalized_query)
        lexical_dict = lexical_engine.forward(normalized_query)
        dict_rrf_score = compute_rrf(lexical_dict, semantic_dict, mask=one_mask)
        #get keys of dict_rrf_score
        top_k_indexes = [int(idx) for idx in dict_rrf_score.keys()]
        top_k_indexes = sorted(top_k_indexes, key=lambda x: dict_rrf_score[x], reverse=True)
        top_k_indexes = top_k_indexes[:10]
        print(top_k_indexes)
        context = ""
        print(f"len(knowledge) : {len(knowledge)}")
        for index in top_k_indexes:
            context += f"{knowledge[index]}\n"
        truncated_context = self._truncate_text(context, 200)
        print(f"context : {truncated_context}")
        return context
        
    def _classify_query_category(self, query: str) -> str:
        """
        Classify user query into a category tag using simple keyword matching.
        This is a lightweight classification for SQL masking.
        """
        query_lower = query.lower()
        
        # Define keyword mapping for common categories
        category_mappings = {
            "ฉีดวัคซีน HPV (HPV Vaccine)": ["hpv", "วัคซีน hpv", "cervical cancer", "มะเร็งปากมดลูก"],
            "โปรแกรมตรวจสุขภาพ (Health Checkup)": ["ตรวจสุขภาพ", "health checkup", "checkup", "ตรวจร่างกาย"],
            "ตรวจตับ (Liver Function Test)": ["ตรวจตับ", "liver", "ไขมันพอกตับ", "fibroscan"],
            "ตรวจภูมิแพ้และภาวะแพ้ (Allergy Test)": ["ภูมิแพ้", "allergy", "แพ้", "allergen"],
            "ตรวจการนอน (Sleep Test)": ["การนอน", "sleep", "นอนกรน", "sleep apnea"],
            "ตรวจระดับฮอร์โมน (Hormone Test)": ["ฮอร์โมน", "hormone", "testosterone", "estrogen"],
            "ฟอกสีฟัน (Teeth Whitening)": ["ฟอกสีฟัน", "teeth whitening", "ฟอกฟัน", "cool light"],
            "อุดฟัน (Dental Filling)": ["อุดฟัน", "dental filling", "อุด", "ฟันผุ"],
            "ถอนหรือผ่าฟันคุด": ["ฟันคุด", "wisdom tooth", "ถอนฟัน", "ผ่าฟัน"],
            "กำจัดขนรักแร้ (Armpit Hair Removal)": ["กำจัดขน", "hair removal", "รักแร้", "armpit", "laser hair"],
            "ทำ Pico Laser": ["pico", "laser", "picosecond", "ปิโก"],
            "ทำอัลเทอร์รา (Ulthera)": ["ulthera", "อัลเทอร์รา", "ultherapy", "ยกกระชับ"],
            "ทำ Morpheus 8": ["morpheus", "มอร์เฟียส", "morpheus 8", "rf microneedling"],
            "รักษาหลุมสิว ลดรอยสิว": ["หลุมสิว", "รอยสิว", "acne scar", "สิว", "subcision"],
            "รักษาแผลเป็นคีลอยด์ (keloid treatment)": ["คีลอยด์", "keloid", "แผลเป็น", "scar"],
            "ตรวจโรคติดต่อทางเพศสัมพันธ์ (STD)": ["std", "โรคติดต่อทางเพศ", "sexually transmitted", "ติดต่อทางเพศ"],
            "ตรวจมะเร็งสำหรับผู้หญิง": ["มะเร็งเต้านม", "breast cancer", "มะเร็งปากมดลูก", "thinprep", "mammogram"],
            "ลดเหงื่อ ลดกลิ่นตัว": ["เหงื่อ", "กลิ่นตัว", "botox armpit", "reduce sweat"],
            "ตรวจก่อนแต่งงาน (Pre-Marriage Checkup)": ["ก่อนแต่งงาน", "pre marriage", "ก่อนมีลูก", "pre pregnancy"],
            "ฉีดวัคซีนไข้หวัดใหญ่ (Influenza Vaccine)": ["ไข้หวัดใหญ่", "influenza", "flu vaccine", "วัคซีนไข้หวัด"],
        }
        
        # Check for keyword matches
        for category, keywords in category_mappings.items():
            for keyword in keywords:
                if keyword in query_lower:
                    return category
        
        # Check for price-based queries - could be any category
        if any(price_word in query_lower for price_word in ["ราคา", "price", "บาท", "baht", "cost"]):
            # For price queries, try to extract the main topic
            for category, keywords in category_mappings.items():
                for keyword in keywords:
                    if keyword in query_lower:
                        return category
        
        return "<UNKNOWN>"

    def _get_sql_category_mask(self, category_tag: str):
        """
        Create a filtered DataFrame based on category tag for SQL operations.
        Returns filtered knowledge_base DataFrame.
        """
        if category_tag == "<UNKNOWN>" or not hasattr(self, 'hl_map'):
            return self.knowledge_base
        
        # Find package URLs for this category
        package_urls = []
        for d in self.hl_map:
            if d['cat_name'] == category_tag:
                package_urls = d['packages']
                break
        
        if not package_urls:
            return self.knowledge_base
        
        # Filter knowledge_base to only include rows with URLs from this category
        filtered_kb = self.knowledge_base[self.knowledge_base['URL'].isin(package_urls)]
        
        print(f"🎯 Category Filter: {category_tag} ({len(self.knowledge_base)} → {len(filtered_kb)} rows)")
        
        return filtered_kb if len(filtered_kb) > 0 else self.knowledge_base

    # Column mapping for robust SQL queries
    COLUMN_MAPPINGS = {
        'package_name': ['package_name', 'Package Name', 'Name'],
        'hdmall_price': ['hdmall_price', 'HDmall Price', 'HDmall_Price', 'price', 'Cash Price'],
        'brand': ['brand', 'Brand'],
        'category': ['category', 'Category'],
        'location': ['location', 'Location']
    }

    def normalize_column_name(self, df, target_column):
        """Normalize column names to standard format"""
        for standard_name, variants in self.COLUMN_MAPPINGS.items():
            if target_column.lower() in [v.lower() for v in variants]:
                for variant in variants:
                    if variant in df.columns:
                        return variant
        return None

    def validate_and_fix_query(self, query_str, df):
        """Validate and fix column names in SQL queries"""
        import re
        
        # Find all column references in query
        column_pattern = r"kb\['([^']+)'\]"
        columns_in_query = re.findall(column_pattern, query_str)
        
        # Replace with actual column names
        for col in columns_in_query:
            actual_col = self.normalize_column_name(df, col)
            if actual_col and actual_col != col:
                query_str = query_str.replace(f"kb['{col}']", f"kb['{actual_col}']")
                logger.info(f"🔄 [SQL-FIX] Mapped column '{col}' → '{actual_col}'")
        
        return query_str

    def sql_search(self, query: str, category_tag: str = "") -> str:
        """
        Execute SQL-like query on the knowledge base with category masking.
        Handles both pandas query syntax and raw SQL, converting as needed.
        Returns a string representation of only essential metadata columns to save tokens.
        
        Args:
            query: The pandas query string to execute
            category_tag: The category to filter by (provided by LLM)
        """
        try:
            # Initialize knowledge_base if not already done
            if self.knowledge_base is None:
                self.knowledge_base = self.global_storage.knowledge_base

            # Use the LLM-provided category tag directly
            # If empty, use <UNKNOWN> to indicate no category filtering
            if not category_tag.strip():
                category_tag = "<UNKNOWN>"
            
            # Apply category mask to filter dataset
            filtered_kb = self._get_sql_category_mask(category_tag)

            # Validate and fix column names in query
            fixed_query = self.validate_and_fix_query(query, filtered_kb)
            
            # Apply brand normalization to the query
            # Look for brand-related patterns in the query and normalize them
            normalized_query = self._normalize_query_brands(fixed_query)

            # Replace all knowledge_base references with kb for consistency
            normalized_query = normalized_query.replace("knowledge_base", "kb")
            
            # Create local context for eval with filtered dataset
            local_context = {
                "kb": filtered_kb,  # Use filtered dataset instead of full knowledge_base
                "pd": pd,
                "np": np
            }
            
            # Check if it's a SQL-style query
            if "SELECT" in normalized_query.upper() and "FROM" in normalized_query.upper():
                # For SQL queries, we'll convert to pandas operations
                if "WHERE" in normalized_query.upper():
                    # Extract the WHERE clause and convert to pandas filter
                    where_part = normalized_query.split("WHERE")[1].split("ORDER BY")[0] if "ORDER BY" in normalized_query.upper() else normalized_query.split("WHERE")[1]
                    where_part = where_part.strip()
                    
                    # Simple replacements for SQL to pandas
                    where_part = where_part.replace("LIKE", ".str.contains")
                    where_part = where_part.replace("'%", "'")
                    where_part = where_part.replace("%'", "'")
                    where_part = where_part.replace(" AND ", " & ")
                    where_part = where_part.replace(" OR ", " | ")
                    
                    # Build the pandas query
                    pandas_query = f"kb[{where_part}]"
                    
                    # Handle ORDER BY
                    if "ORDER BY" in normalized_query.upper():
                        order_part = normalized_query.split("ORDER BY")[1].strip()
                        sort_col = order_part.split()[0].strip('"').strip("'")
                        ascending = "ASC" in order_part.upper()
                        pandas_query += f".sort_values('{sort_col}', ascending={ascending})"
                    
                    # Add head limit
                    pandas_query += ".head(15)"
                    
                    result = eval(pandas_query, {"__builtins__": {}}, local_context)
                else:
                    # Simple SELECT without WHERE
                    result = filtered_kb.head(15)
            else:
                # Direct pandas query or expression
                try:
                    # Try as pandas expression first
                    if any(op in normalized_query for op in ['[', '&', '|', '.str.', '.head(', '.sort_values(']):
                        # This looks like a pandas expression
                        result = eval(normalized_query, {"__builtins__": {}}, local_context)
                    else:
                        # Try as pandas query method
                        result = filtered_kb.query(normalized_query).head(15)
                except:
                    # Fallback to eval
                    result = eval(normalized_query, {"__builtins__": {}}, local_context)
            
            # Define essential metadata columns to save tokens (similar to _get_package_url)
            essential_columns = [
                'Name', 'URL', 'Brand', 'Category', 'location',
                'Original Price', 'HDmall Price', 'Cash Discount', 'Cash Price', 
                'Deposit Price', 'Full or Starting Price'
            ]
            
            # Filter to only essential columns that exist in the result
            if hasattr(result, 'columns'):
                available_columns = [col for col in essential_columns if col in result.columns]
                if available_columns:
                    # Select only essential columns
                    result_filtered = result[available_columns]
                else:
                    # If no essential columns found, take first 6 columns to limit tokens
                    result_filtered = result.iloc[:, :6] if len(result.columns) > 6 else result
            else:
                result_filtered = result
            
            # Convert DataFrame to structured string representation (more readable than to_string())
            if hasattr(result_filtered, 'iterrows'):
                result_str = f"SQL Search Results ({len(result_filtered)} packages found):\n"
                result_str += "="*60 + "\n"
                
                for idx, (_, row) in enumerate(result_filtered.iterrows(), 1):
                    result_str += f"\n📦 PACKAGE {idx}:\n"
                    result_str += f"   Name: {row.get('Name', 'N/A')}\n"
                    result_str += f"   URL: {row.get('URL', 'N/A')}\n"
                    result_str += f"   Brand: {row.get('Brand', 'N/A')}\n"
                    result_str += f"   Category: {row.get('Category', 'N/A')}\n"
                    result_str += f"   Location: {row.get('location', 'N/A')}\n"
                    
                    # Price information
                    if 'Cash Price' in row:
                        result_str += f"   💰 Cash Price: {row.get('Cash Price', 'N/A')} ฿\n"
                    if 'HDmall Price' in row:
                        result_str += f"   💳 HDmall Price: {row.get('HDmall Price', 'N/A')} ฿\n"
                    if 'Original Price' in row:
                        result_str += f"   🏷️ Original Price: {row.get('Original Price', 'N/A')} ฿\n"
                    
                    result_str += "   " + "-"*50 + "\n"
                
                result_str += f"\n📊 Total Results: {len(result_filtered)} packages\n"
                result_str += "="*60
            else:
                result_str = str(result_filtered)
            
            # Print the results for debugging (without verbose context)
            print(f"🔍 SQL Search Query: {normalized_query}")
            print(f"🎯 LLM-provided Category: {category_tag}")
            print(f"📊 Results: {len(result) if hasattr(result, '__len__') else 'N/A'} rows found")
            print(f"💾 Token Optimization: Showing only essential metadata columns")
            if normalized_query != query:
                print(f"📝 Original Query: {query}")
            print("="*50)
                
            return result_str
            
        except Exception as e:
            logger.error(f"Error in sql_search: {str(e)}")
            logger.error(f"Query was: {query}")
            # Return error message as string
            return f"Error executing query: {str(e)}\nQuery was: {query}"

    def _normalize_query_brands(self, query: str) -> str:
        """
        Normalize brand names within SQL queries.
        Looks for brand references and replaces abbreviations with full names.
        """
        import re
        
        # Pattern to find brand references in queries
        # Matches things like Brand.str.contains('baac') or Brand == 'BAAC'
        brand_patterns = [
            r"Brand\.str\.contains\(['\"]([^'\"]+)['\"]",  # Brand.str.contains('baac')
            r"Brand\s*==\s*['\"]([^'\"]+)['\"]",          # Brand == 'baac'
            r"Brand\s*=\s*['\"]([^'\"]+)['\"]",           # Brand = 'baac'
        ]
        
        normalized_query = query
        
        for pattern in brand_patterns:
            matches = re.finditer(pattern, normalized_query, re.IGNORECASE)
            for match in matches:
                original_brand = match.group(1)
                normalized_brand = self.normalize_brand_name(original_brand)
                
                if normalized_brand != original_brand:
                    # Replace the original brand with normalized brand in the query
                    old_part = match.group(0)
                    new_part = old_part.replace(original_brand, normalized_brand)
                    normalized_query = normalized_query.replace(old_part, new_part)
                    print(f"🏥 Brand normalization: '{original_brand}' → '{normalized_brand}'")
        
        return normalized_query

    def explore_data_structure(self, exploration_type: str) -> str:
        """
        Explore the knowledge base structure to understand available data.
        Returns insights about the database content.
        """
        try:
            # Initialize knowledge_base if not already done
            if self.knowledge_base is None:
                self.knowledge_base = self.global_storage.knowledge_base
            
            if exploration_type == "columns":
                # Show all available columns
                columns = list(self.knowledge_base.columns)
                result = f"Available columns in the database:\n"
                for i, col in enumerate(columns, 1):
                    result += f"{i}. {col}\n"
                result += f"\nTotal: {len(columns)} columns"
                
            elif exploration_type == "unique_brands":
                # Show unique brands/hospitals
                unique_brands = self.knowledge_base['Brand'].dropna().unique()
                result = f"Available Brands/Hospitals ({len(unique_brands)} total):\n"
                for i, brand in enumerate(sorted(unique_brands), 1):
                    result += f"{i}. {brand}\n"
                    
            elif exploration_type == "unique_categories":
                # Show unique categories
                unique_categories = self.knowledge_base['Category'].dropna().unique()
                result = f"Available Categories ({len(unique_categories)} total):\n"
                for i, category in enumerate(sorted(unique_categories), 1):
                    result += f"{i}. {category}\n"
                    
            elif exploration_type == "sample_data":
                # Show 10 random samples with key columns
                sample_data = self.knowledge_base[['Name', 'Brand', 'Category', 'Cash Price', 'location']].sample(n=min(10, len(self.knowledge_base)))
                result = f"Sample data (10 random rows):\n"
                result += sample_data.to_string()
                
            elif exploration_type == "price_range":
                # Show price statistics
                price_col = 'Cash Price'
                if price_col in self.knowledge_base.columns:
                    prices = self.knowledge_base[price_col].dropna()
                    result = f"Price Range Analysis:\n"
                    result += f"Minimum Price: {prices.min():,.0f} ฿\n"
                    result += f"Maximum Price: {prices.max():,.0f} ฿\n"
                    result += f"Average Price: {prices.mean():,.0f} ฿\n"
                    result += f"Median Price: {prices.median():,.0f} ฿\n"
                    result += f"\nPrice Distribution:\n"
                    result += f"Under 1,000฿: {len(prices[prices < 1000])} packages\n"
                    result += f"1,000-5,000฿: {len(prices[(prices >= 1000) & (prices < 5000)])} packages\n"
                    result += f"5,000-10,000฿: {len(prices[(prices >= 5000) & (prices < 10000)])} packages\n"
                    result += f"10,000฿+: {len(prices[prices >= 10000])} packages\n"
                else:
                    result = "Price column not found in the database"
                    
            elif exploration_type == "unique_locations":
                # Show unique locations
                unique_locations = self.knowledge_base['location'].dropna().unique()
                # Take first 50 locations to avoid overwhelming output
                result = f"Available Locations ({len(unique_locations)} total, showing first 50):\n"
                for i, location in enumerate(sorted(unique_locations)[:50], 1):
                    result += f"{i}. {location}\n"
                if len(unique_locations) > 50:
                    result += f"... and {len(unique_locations) - 50} more locations"
                    
            else:
                result = f"Unknown exploration type: {exploration_type}"
                
            print(f"Data Structure Exploration ({exploration_type}):")
            print(result)
            print("="*50)
            
            return result
            
        except Exception as e:
            logger.error(f"Error in explore_data_structure: {str(e)}")
            return f"Error exploring data structure: {str(e)}"

    def smart_search_suggestions(self, failed_query_type: str, original_search_term: str) -> str:
        """
        Provide intelligent search suggestions when queries fail.
        Uses fuzzy matching to find similar alternatives.
        """
        try:
            # Initialize knowledge_base if not already done
            if self.knowledge_base is None:
                self.knowledge_base = self.global_storage.knowledge_base
            
            import difflib
            
            # First try to normalize the search term
            normalized_term = original_search_term
            if failed_query_type == "brand":
                normalized_term = self.normalize_brand_name(original_search_term)
                if normalized_term != original_search_term:
                    print(f"Smart suggestions brand normalization: '{original_search_term}' → '{normalized_term}'")
                    # Check if the normalized term exists in the database
                    exact_matches = self.knowledge_base[
                        self.knowledge_base['Brand'].str.contains(normalized_term, case=False, na=False)
                    ]
                    if len(exact_matches) > 0:
                        result = f"Found exact match after normalization:\n"
                        result += f"'{original_search_term}' → '{normalized_term}'\n"
                        result += f"Found {len(exact_matches)} packages from '{normalized_term}'\n"
                        print(f"Smart Search Suggestions ({failed_query_type}) - EXACT MATCH FOUND:")
                        print(result)
                        print("="*50)
                        return result
            
            if failed_query_type == "brand":
                # Find similar brand names
                unique_brands = self.knowledge_base['Brand'].dropna().unique()
                similar_brands = difflib.get_close_matches(
                    normalized_term, unique_brands, n=5, cutoff=0.3
                )
                
                result = f"'{original_search_term}' not found. Similar brands:\n"
                if similar_brands:
                    for i, brand in enumerate(similar_brands, 1):
                        count = len(self.knowledge_base[self.knowledge_base['Brand'] == brand])
                        result += f"{i}. {brand} ({count} packages)\n"
                else:
                    result += "No similar brands found. Here are the most popular brands:\n"
                    brand_counts = self.knowledge_base['Brand'].value_counts().head(10)
                    for i, (brand, count) in enumerate(brand_counts.items(), 1):
                        result += f"{i}. {brand} ({count} packages)\n"
                    
            elif failed_query_type == "category":
                # Find similar categories
                unique_categories = self.knowledge_base['Category'].dropna().unique()
                similar_categories = difflib.get_close_matches(
                    original_search_term, unique_categories, n=5, cutoff=0.3
                )
                
                result = f"'{original_search_term}' not found. Similar categories:\n"
                if similar_categories:
                    for i, category in enumerate(similar_categories, 1):
                        count = len(self.knowledge_base[self.knowledge_base['Category'] == category])
                        result += f"{i}. {category} ({count} packages)\n"
                else:
                    result += "No similar categories found. Here are the most popular categories:\n"
                    category_counts = self.knowledge_base['Category'].value_counts().head(10)
                    for i, (category, count) in enumerate(category_counts.items(), 1):
                        result += f"{i}. {category} ({count} packages)\n"
                        
            elif failed_query_type == "package_name":
                # Find similar package names
                package_names = self.knowledge_base['Name'].dropna().unique()
                similar_packages = difflib.get_close_matches(
                    original_search_term, package_names, n=5, cutoff=0.3
                )
                
                result = f"'{original_search_term}' not found. Similar packages:\n"
                if similar_packages:
                    for i, package in enumerate(similar_packages, 1):
                        # Get the brand and price for context
                        pkg_info = self.knowledge_base[self.knowledge_base['Name'] == package].iloc[0]
                        result += f"{i}. {package}\n   Brand: {pkg_info['Brand']}, Price: {pkg_info['Cash Price']:,.0f}฿\n"
                else:
                    result += "No similar package names found."
                    
            elif failed_query_type == "location":
                # Find similar locations
                unique_locations = self.knowledge_base['location'].dropna().unique()
                similar_locations = difflib.get_close_matches(
                    original_search_term, unique_locations, n=5, cutoff=0.3
                )
                
                result = f"'{original_search_term}' not found. Similar locations:\n"
                if similar_locations:
                    for i, location in enumerate(similar_locations, 1):
                        count = len(self.knowledge_base[self.knowledge_base['location'].str.contains(location, case=False, na=False)])
                        result += f"{i}. {location} ({count} packages)\n"
                else:
                    result += "No similar locations found. Here are areas with most packages:\n"
                    # Extract common location terms
                    all_locations = ' '.join(self.knowledge_base['location'].dropna().astype(str))
                    common_areas = ['กรุงเทพ', 'บางกอก', 'Bangkok', 'สยาม', 'ชิดลม', 'ปทุมวัน', 'ราชเทวี']
                    for area in common_areas:
                        count = self.knowledge_base['location'].str.contains(area, case=False, na=False).sum()
                        if count > 0:
                            result += f"- {area}: {count} packages\n"
                            
            elif failed_query_type == "price":
                # Suggest alternative price ranges
                prices = self.knowledge_base['Cash Price'].dropna()
                try:
                    target_price = float(original_search_term.replace(',', '').replace('฿', '').replace('บาท', ''))
                    
                    result = f"No packages found for {target_price:,.0f}฿. Alternative price ranges:\n"
                    
                    # Find packages within +/- 50% of target price
                    lower_bound = target_price * 0.5
                    upper_bound = target_price * 1.5
                    
                    nearby_packages = self.knowledge_base[
                        (prices >= lower_bound) & (prices <= upper_bound)
                    ]
                    
                    if len(nearby_packages) > 0:
                        result += f"Packages between {lower_bound:,.0f}฿ - {upper_bound:,.0f}฿: {len(nearby_packages)} found\n"
                        
                        # Show cheapest and most expensive in this range
                        cheapest = nearby_packages.loc[prices.idxmin()]
                        most_expensive = nearby_packages.loc[prices.idxmax()]
                        
                        result += f"Cheapest: {cheapest['Name']} - {cheapest['Cash Price']:,.0f}฿\n"
                        result += f"Most expensive: {most_expensive['Name']} - {most_expensive['Cash Price']:,.0f}฿\n"
                    else:
                        result += "No packages found in nearby price ranges.\n"
                        result += f"Cheapest package overall: {prices.min():,.0f}฿\n"
                        result += f"Most expensive package overall: {prices.max():,.0f}฿\n"
                        
                except ValueError:
                    result = f"Could not parse price: {original_search_term}"
                    
            else:
                result = f"Unknown failed query type: {failed_query_type}"
                
            print(f"Smart Search Suggestions ({failed_query_type}):")
            print(result)
            print("="*50)
            
            return result
            
        except Exception as e:
            logger.error(f"Error in smart_search_suggestions: {str(e)}")
            return f"Error generating suggestions: {str(e)}"

    def sql_search_with_category(self, query: str, category_override: str = None) -> str:
        """
        Convenience method to perform SQL search with explicit category override.
        
        Args:
            query: SQL query string
            category_override: Override automatic category detection with specific category
        """
        if category_override:
            # Temporarily store auto-detected category
            original_method = self._classify_query_category
            self._classify_query_category = lambda x: category_override
            
            try:
                result = self.sql_search(query)
            finally:
                # Restore original method
                self._classify_query_category = original_method
            
            return result
        else:
            return self.sql_search(query)