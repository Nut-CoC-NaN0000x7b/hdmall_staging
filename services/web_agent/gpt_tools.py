class GPTTools:
    search_package_database = {
    "type": "function",
    "function": {
        "name": "search_package_database",
        "description": "Retrieves relavent packages metadata from our HDmall database. Metadata including [Name, price, location, Brand]",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "thought": {
                    "type": "string",
                    "description": "your thinking step by step on why you calling this tool and what you will do with the results"
                },
                "package_name": {
                    "type": "string",
                    "description": "package name"
                },
                "location": {
                    "type": "string",
                    "description": "user preferred location"
                },
                "price": {
                    "type": "string",
                    "description": "user preferred price"
                },
                "brand": {
                    "type": "string",
                    "description": "user preferred brand"
                },
                "category_tag": {
                    "type": "string",
                    "description": """ <category_tag_list> 

    <category index=1>
      <cat_name>ตรวจกระดูก</cat_name>
      <hl_url>https://hdmall.co.th/highlight/osteoporosis</hl_url>
    </category index=1>
    
    <category index=2>
      <cat_name>กายภาพบำบัดออฟฟิศซินโดรม (Physical Therapy Office Syndrome)</cat_name>
      <hl_url>https://hdmall.co.th/highlight/office-syndrome</hl_url>
    </category index=2>
    
    <category index=3>
      <cat_name>ฟอกสีฟัน (Teeth Whitening)</cat_name>
      <hl_url>https://hdmall.co.th/highlight/teeth-whitening</hl_url>
    </category index=3>
    
    <category index=6>
      <cat_name>ตรวจตับ (Liver Function Test)</cat_name>
      <hl_url>https://hdmall.co.th/highlight/liver-checkup-oneprice</hl_url>
    </category index=6>
    
    <category index=7>
      <cat_name>ตรวจภูมิแพ้และภาวะแพ้ (Allergy Test)</cat_name>
      <hl_url>https://hdmall.co.th/highlight/allergy-test</hl_url>
    </category index=7>
    
    <category index=8>
      <cat_name>จี้ไฝ กระ และรอยปาน</cat_name>
      <hl_url>https://hdmall.co.th/highlight/co2-laser-2025</hl_url>
    </category index=8>
    
    <category index=10>
      <cat_name>กำจัดขนรักแร้ (Armpit Hair Removal)</cat_name>
      <hl_url>https://hdmall.co.th/highlight/armpit-hair-removal-oneprice</hl_url>
    </category index=10>
    
    <category index=11>
      <cat_name>ตรวจ รักษาไทรอยด์</cat_name>
      <hl_url>https://hdmall.co.th/highlight/thyroid-screening-oneprice</hl_url>
    </category index=11>
    
    <category index=13>
      <cat_name>อุดฟัน (Dental Filling)</cat_name>
      <hl_url>https://hdmall.co.th/highlight/dental-filling</hl_url>
    </category index=13>
    
    <category index=16>
      <cat_name>รักษารอยแตกลาย รอยคล้ำ (Stretch Marks Treatment)</cat_name>
      <hl_url>https://hdmall.co.th/highlight/dark-marks-laser</hl_url>
    </category index=16>
    
    <category index=17>
      <cat_name>ตรวจภูมิแพ้อาหารแฝง (Food Intolerance Test)</cat_name>
      <hl_url>https://hdmall.co.th/highlight/food-intolerance-test</hl_url>
    </category index=17>
    
    <category index=19>
      <cat_name>ตรวจการนอน (Sleep Test)</cat_name>
      <hl_url>https://hdmall.co.th/highlight/sleep-test</hl_url>
    </category index=19>
    
    <category index=20>
      <cat_name>ทำรีเทนเนอร์แบบลวด (Hawley Retainer)</cat_name>
      <hl_url>https://hdmall.co.th/highlight/retainer-one-price</hl_url>
    </category index=20>
    
    <category index=21>
      <cat_name>ฉีดวัคซีนไข้หวัดใหญ่ (Influenza Vaccine)</cat_name>
      <hl_url>https://hdmall.co.th/highlight/influenza-dengue-vaccine</hl_url>
    </category index=21>
    
    <category index=22>
      <cat_name>ทำ Pico Laser</cat_name>
      <hl_url>https://hdmall.co.th/highlight/pico-laser-2025</hl_url>
    </category index=22>
    
    <category index=23>
      <cat_name>โปรแกรมตรวจสุขภาพ (Health Checkup)</cat_name>
      <hl_url>https://hdmall.co.th/highlight/health-checkup-oneprice</hl_url>
    </category index=23>
    
    <category index=25>
      <cat_name>ทำรีเทนเนอร์ใส (Clear Retainer)</cat_name>
      <hl_url>https://hdmall.co.th/highlight/retainer-one-price</hl_url>
    </category index=25>
    
    <category index=26>
      <cat_name>ตรวจก่อนแต่งงาน (Pre-Marriage Checkup)</cat_name>
      <hl_url>https://hdmall.co.th/highlight/prepregnancy</hl_url>
    </category index=26>
    
    <category index=29>
      <cat_name>ตรวจระดับฮอร์โมน (Hormone Test)</cat_name>
      <hl_url>https://hdmall.co.th/highlight/hormone-test-hdmall-plus</hl_url>
    </category index=29>
    
    <category index=31>
      <cat_name>ทำ Morpheus 8</cat_name>
      <hl_url>https://hdmall.co.th/highlight/morpheus-8</hl_url>
    </category index=31>
    
    <category index=32>
      <cat_name>ทำอัลเทอร์รา (Ulthera)</cat_name>
      <hl_url>https://hdmall.co.th/highlight/ultherapy</hl_url>
    </category index=32>
    
    <category index=33>
      <cat_name>รักษาหลุมสิว ลดรอยสิว</cat_name>
      <hl_url>https://hdmall.co.th/highlight/acne-scars</hl_url>
    </category index=33>
    
    <category index=34>
      <cat_name>ฉีดวัคซีน HPV (HPV Vaccine)</cat_name>
      <hl_url>https://hdmall.co.th/highlight/msd-hpv-vaccine</hl_url>
    </category index=34>
    
    <category index=35>
      <cat_name>ตรวจโรคติดต่อทางเพศสัมพันธ์ (STD)</cat_name>
      <hl_url>https://hdmall.co.th/highlight/std-check-sure</hl_url>
    </category index=35>
    
    <category index=36>
      <cat_name>รักษาแผลเป็นคีลอยด์ (keloid treatment)</cat_name>
      <hl_url>https://hdmall.co.th/highlight/keloid</hl_url>
    </category index=36>
    
    <category index=37>
      <cat_name>ตรวจมะเร็งสำหรับผู้หญิง</cat_name>
      <hl_url>https://hdmall.co.th/highlight/women_cancer-hl</hl_url>
    </category index=37>
    
    <category index=38>
      <cat_name>ถอนหรือผ่าฟันคุด</cat_name>
      <hl_url>https://hdmall.co.th/highlight/wisdom-teeth-test</hl_url>
    </category index=38>
    
    <category index=39>
      <cat_name>ลดเหงื่อ ลดกลิ่นตัว</cat_name>
      <hl_url>https://hdmall.co.th/highlight/armpit-botulinum-toxin-program</hl_url>
    </category index=39>
    
    <category index=40>
      <cat_name>รักษาสิว (Acne Treatment)</cat_name>
      <hl_url>https://hdmall.co.th/highlight/acne-program</hl_url>
    </category index=40>
    </category_tag_list>

    from <category_tags> you can choose one of the following tags if it's related to the user's query. leave it as "" if none if these categories are related to the user's query.
    When selecting category_tag, you should only provide message in <cat_name> tag. like for for example:
    User_query : สนใจ hpv วัคซีนค่ะ
    Your Output for this argument: ฉีดวัคซีน HPV (HPV Vaccine)
    
"""
                }
            },
            "required": ["thought", "package_name", "location", "price", "brand", "category_tag"],
            "additionalProperties": False
        }
    }
}

    fetch_package_details = {
        "type": "function",
        "function": {
            "name": "fetch_package_details",
            "description": "Fetches detailed information about a specific package from HDmall using the package URL. Returns comprehensive package details including specifications, pricing, availability, and provider information.",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "thought": {
                        "type": "string",
                        "description": "your thinking step by step on why you calling this tool and what you will do with the results"
                    },
                    "package_url": {
                        "type": "string",
                        "description": "the full URL of the package to fetch details for, use search_package_database tool to get the package url if user doesn't provide it"
                    }
                },
                "required": ["thought", "package_url"],
                "additionalProperties": False
            }
        }
    }

    browse_broad_pages = {
        "type": "function",
        "function": {
            "name": "browse_broad_pages",
            "description": """- Browse broader category pages and landing pages on HDmall to discover packages and services. Useful for exploring general categories or when users have broad queries.
            - for 'brand' queries, you ALWAYS use full brand name as query.
            """,
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "thought": {
                        "type": "string",
                        "description": "your thinking step by step on why you calling this tool and what you will do with the results"
                    },
                    "query": {
                        "type": "string",
                        "description": "the search query or topic to browse for"
                    },
                    "page_type": {
                        "type": "string",
                        "description": """the type of page to browse. Options: 'tag' for tags pages that group related packages with similar medical tags, 'hl' for highlight/featured pages, and 'brand' for brand(hospital/clinic) pages"""
                    }
                },
                "required": ["thought", "query", "page_type"],
                "additionalProperties": False
            }
        }
    }

    cart = {
        "type": "function",
        "function": {
            "name": "cart",
            "description": "Manage shopping cart operations including adding items, removing items, viewing cart contents, and proceeding to checkout.",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "thought": {
                        "type": "string",
                        "description": "your thinking step by step on why you calling this tool and what you will do with the results"
                    },
                    "action": {
                        "type": "string",
                        "description": "the cart action to perform. Options: 'create', 'delete_package' , 'add_package', 'create_payment_url' "
                    },
                    "package_id": {
                        "type": "string",
                        "description": "the package ID when adding or removing items from cart. Leave empty for view, clear, or checkout actions"
                    },
                    "card_id": {
                        "type": "string",
                        "description": "the card id to perform the action on"
                    }
                },
                "required": ["thought", "action", "package_id", "card_id"],
                "additionalProperties": False
            }
        }
    }

    sql_search = {
        "type": "function",
        "function": {
            "name": "sql_search",
            "description": """Search the knowledge base using pandas queries with automatic category masking for more relevant results.
            
            🎯 **NEW ENHANCED FEATURE**: This tool now automatically detects the category from your query and filters the dataset to only include relevant packages from that category before executing your SQL query. This makes searches much more focused and accurate!
            
            **Category Detection Examples**:
            - "HPV under 20k baht" → Auto-detects "ฉีดวัคซีน HPV (HPV Vaccine)" category
            - "health checkup packages under 5000" → Auto-detects "โปรแกรมตรวจสุขภาพ (Health Checkup)" category  
            - "teeth whitening in Bangkok" → Auto-detects "ฟอกสีฟัน (Teeth Whitening)" category
            
            Use this tool when users ask for:
            - Specific filtering criteria (e.g., "cheapest packages", "most expensive")
            - Sorting packages by attributes (e.g., "sort by price", "sort by rating")
            - Limiting the number of results (e.g., "top 5", "first 10")
            - Combining multiple filtering criteria (e.g., "cheapest packages in Bangkok")
            - Category-specific searches (e.g., "HPV vaccines under 15000 baht")
            
            The knowledge_base DataFrame contains these columns:
            - Name: Package name
            - Cash Price: Price in Thai Baht (numeric)
            - Brand: Hospital/clinic name
            - Location: Area/district
            - URL: Package URL
            - Package Picture: Image URL
            - Category: Package category
            - Rating: User rating (if available)
            
            **Query Syntax** (use pandas syntax, NOT raw SQL):
            - `kb[kb['Cash Price'] < 5000].head(10)` - Find packages under 5000 baht
            - `kb.sort_values('Cash Price').head(5)` - Find 5 cheapest packages
            - `kb[kb['Brand'].str.contains('Bangkok', case=False, na=False)]` - Find packages from Bangkok hospitals
            - `kb[kb['Cash Price'].between(3000, 8000)].sort_values('Cash Price')` - Find packages in price range
            
            **Benefits of Category Masking**:
            ✅ More accurate results - only searches relevant category
            ✅ Faster processing - smaller dataset to search  
            ✅ Better context - results are category-specific
            ✅ Automatic detection - no need to specify category manually
            """,
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "thought": {
                        "type": "string",
                        "description": "Your thinking step by step on why you're calling this tool and what you will do with the results. Explain your query strategy and what category you're targeting."
                    },
                    "sql_query": {
                        "type": "string",
                        "description": "The pandas query to search the knowledge base. Use pandas syntax (e.g., kb[kb['Cash Price'] < 5000]) NOT raw SQL. The dataset will be filtered to the specified category before executing your query."
                    },
                    "category_tag": {
                        "type": "string",
                        "description": """ <category_tag_list> 

    <category index=1>
      <cat_name>ตรวจกระดูก</cat_name>
      <hl_url>https://hdmall.co.th/highlight/osteoporosis</hl_url>
    </category index=1>
    
    <category index=2>
      <cat_name>กายภาพบำบัดออฟฟิศซินโดรม (Physical Therapy Office Syndrome)</cat_name>
      <hl_url>https://hdmall.co.th/highlight/office-syndrome</hl_url>
    </category index=2>
    
    <category index=3>
      <cat_name>ฟอกสีฟัน (Teeth Whitening)</cat_name>
      <hl_url>https://hdmall.co.th/highlight/teeth-whitening</hl_url>
    </category index=3>
    
    <category index=6>
      <cat_name>ตรวจตับ (Liver Function Test)</cat_name>
      <hl_url>https://hdmall.co.th/highlight/liver-checkup-oneprice</hl_url>
    </category index=6>
    
    <category index=7>
      <cat_name>ตรวจภูมิแพ้และภาวะแพ้ (Allergy Test)</cat_name>
      <hl_url>https://hdmall.co.th/highlight/allergy-test</hl_url>
    </category index=7>
    
    <category index=8>
      <cat_name>จี้ไฝ กระ และรอยปาน</cat_name>
      <hl_url>https://hdmall.co.th/highlight/co2-laser-2025</hl_url>
    </category index=8>
    
    <category index=10>
      <cat_name>กำจัดขนรักแร้ (Armpit Hair Removal)</cat_name>
      <hl_url>https://hdmall.co.th/highlight/armpit-hair-removal-oneprice</hl_url>
    </category index=10>
    
    <category index=11>
      <cat_name>ตรวจ รักษาไทรอยด์</cat_name>
      <hl_url>https://hdmall.co.th/highlight/thyroid-screening-oneprice</hl_url>
    </category index=11>
    
    <category index=13>
      <cat_name>อุดฟัน (Dental Filling)</cat_name>
      <hl_url>https://hdmall.co.th/highlight/dental-filling</hl_url>
    </category index=13>
    
    <category index=16>
      <cat_name>รักษารอยแตกลาย รอยคล้ำ (Stretch Marks Treatment)</cat_name>
      <hl_url>https://hdmall.co.th/highlight/dark-marks-laser</hl_url>
    </category index=16>
    
    <category index=17>
      <cat_name>ตรวจภูมิแพ้อาหารแฝง (Food Intolerance Test)</cat_name>
      <hl_url>https://hdmall.co.th/highlight/food-intolerance-test</hl_url>
    </category index=17>
    
    <category index=19>
      <cat_name>ตรวจการนอน (Sleep Test)</cat_name>
      <hl_url>https://hdmall.co.th/highlight/sleep-test</hl_url>
    </category index=19>
    
    <category index=20>
      <cat_name>ทำรีเทนเนอร์แบบลวด (Hawley Retainer)</cat_name>
      <hl_url>https://hdmall.co.th/highlight/retainer-one-price</hl_url>
    </category index=20>
    
    <category index=21>
      <cat_name>ฉีดวัคซีนไข้หวัดใหญ่ (Influenza Vaccine)</cat_name>
      <hl_url>https://hdmall.co.th/highlight/influenza-dengue-vaccine</hl_url>
    </category index=21>
    
    <category index=22>
      <cat_name>ทำ Pico Laser</cat_name>
      <hl_url>https://hdmall.co.th/highlight/pico-laser-2025</hl_url>
    </category index=22>
    
    <category index=23>
      <cat_name>โปรแกรมตรวจสุขภาพ (Health Checkup)</cat_name>
      <hl_url>https://hdmall.co.th/highlight/health-checkup-oneprice</hl_url>
    </category index=23>
    
    <category index=25>
      <cat_name>ทำรีเทนเนอร์ใส (Clear Retainer)</cat_name>
      <hl_url>https://hdmall.co.th/highlight/retainer-one-price</hl_url>
    </category index=25>
    
    <category index=26>
      <cat_name>ตรวจก่อนแต่งงาน (Pre-Marriage Checkup)</cat_name>
      <hl_url>https://hdmall.co.th/highlight/prepregnancy</hl_url>
    </category index=26>
    
    <category index=29>
      <cat_name>ตรวจระดับฮอร์โมน (Hormone Test)</cat_name>
      <hl_url>https://hdmall.co.th/highlight/hormone-test-hdmall-plus</hl_url>
    </category index=29>
    
    <category index=31>
      <cat_name>ทำ Morpheus 8</cat_name>
      <hl_url>https://hdmall.co.th/highlight/morpheus-8</hl_url>
    </category index=31>
    
    <category index=32>
      <cat_name>ทำอัลเทอร์รา (Ulthera)</cat_name>
      <hl_url>https://hdmall.co.th/highlight/ultherapy</hl_url>
    </category index=32>
    
    <category index=33>
      <cat_name>รักษาหลุมสิว ลดรอยสิว</cat_name>
      <hl_url>https://hdmall.co.th/highlight/acne-scars</hl_url>
    </category index=33>
    
    <category index=34>
      <cat_name>ฉีดวัคซีน HPV (HPV Vaccine)</cat_name>
      <hl_url>https://hdmall.co.th/highlight/msd-hpv-vaccine</hl_url>
    </category index=34>
    
    <category index=35>
      <cat_name>ตรวจโรคติดต่อทางเพศสัมพันธ์ (STD)</cat_name>
      <hl_url>https://hdmall.co.th/highlight/std-check-sure</hl_url>
    </category index=35>
    
    <category index=36>
      <cat_name>รักษาแผลเป็นคีลอยด์ (keloid treatment)</cat_name>
      <hl_url>https://hdmall.co.th/highlight/keloid</hl_url>
    </category index=36>
    
    <category index=37>
      <cat_name>ตรวจมะเร็งสำหรับผู้หญิง</cat_name>
      <hl_url>https://hdmall.co.th/highlight/women_cancer-hl</hl_url>
    </category index=37>
    
    <category index=38>
      <cat_name>ถอนหรือผ่าฟันคุด</cat_name>
      <hl_url>https://hdmall.co.th/highlight/wisdom-teeth-test</hl_url>
    </category index=38>
    
    <category index=39>
      <cat_name>ลดเหงื่อ ลดกลิ่นตัว</cat_name>
      <hl_url>https://hdmall.co.th/highlight/armpit-botulinum-toxin-program</hl_url>
    </category index=39>
    
    <category index=40>
      <cat_name>รักษาสิว (Acne Treatment)</cat_name>
      <hl_url>https://hdmall.co.th/highlight/acne-program</hl_url>
    </category index=40>
    </category_tag_list>

    from <category_tags> you can choose one of the following tags if it's related to the user's query. leave it as "" if none if these categories are related to the user's query.
    When selecting category_tag, you should only provide message in <cat_name> tag. like for for example:
    User_query : สนใจ hpv วัคซีนค่ะ
    Your Output for this argument: ฉีดวัคซีน HPV (HPV Vaccine)
    
"""
                    }
                },
                "required": ["thought", "sql_query", "category_tag"],
                "additionalProperties": False
            }
        }
    }

    explore_data_structure = {
        "type": "function",  
        "function": {
            "name": "explore_data_structure",
            "description": """Explore the knowledge base structure to understand available data.
            
            Use this tool when:
            - SQL searches return no results
            - You need to understand what brands, categories, or locations are available
            - User asks for something but you're not sure if it exists in the database
            - You want to show users what options are available
            
            This tool helps you understand the database content before making better search queries.
            """,
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "thought": {
                        "type": "string",
                        "description": "Why you're exploring the data structure and what information you hope to find"
                    },
                    "exploration_type": {
                        "type": "string", 
                        "description": "Type of exploration: 'columns' (show all column names), 'unique_brands' (show unique hospital/clinic brands), 'unique_categories' (show unique service categories), 'sample_data' (show 10 random rows), 'price_range' (show min/max prices), 'unique_locations' (show available locations)"
                    }
                },
                "required": ["thought", "exploration_type"],
                "additionalProperties": False
            }
        }
    }

    smart_search_suggestions = {
        "type": "function",
        "function": {
            "name": "smart_search_suggestions", 
            "description": """Get intelligent search suggestions when queries fail.
            
            Use this tool after failed searches to:
            - Find similar brands when exact brand name doesn't exist
            - Suggest alternative categories when requested category has no results
            - Find packages with similar names when exact match fails
            - Suggest price ranges when user's budget doesn't match any packages
            
            This tool analyzes the user's failed query and suggests better alternatives.
            """,
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "thought": {
                        "type": "string",
                        "description": "Explain what failed in the previous search and what suggestions you're looking for"
                    },
                    "failed_query_type": {
                        "type": "string",
                        "description": "Type of failed search: 'brand' (brand name not found), 'category' (category not found), 'price' (no packages in price range), 'location' (location not found), 'package_name' (package name not found)"
                    },
                    "original_search_term": {
                        "type": "string", 
                        "description": "The original search term that failed (e.g., brand name, category, location, package name)"
                    }
                },
                "required": ["thought", "failed_query_type", "original_search_term"],
                "additionalProperties": False
            }
        }
    } 