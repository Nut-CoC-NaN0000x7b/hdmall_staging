class Tools:
    retrieval = {
    "name" : "retrieval",
    "description" : """
    <what_is_this_tool_doing?>
    This tool will search on packages database with rewritten_query.
    <LIST_OF_INFORMATIONS_YOU_WILL_GET>
        -package_name
        -package_brand
        -package_url
        -package_selling_points
        -package_full_price
        -package_price_at_HDmall_or_buy_with_our_agent
        -package_cash_discount
        -package_price_if_pay_with_cash
        -installment_months_limits
        -installment_rate/max_months
        -price_to_reserve/early_pay
        -package_details
        -payment_method_Thai
        -payment_method_English
        -payment_information
        -package_locations
        -package_important_info
        -package_general_info
        -package_min_or_max_age
        -package_common_question
        -package_comparisons
        -package_review
        -package_FAQ
        -pharmacy
        -coupon
        -credit_cards_promotion
        </LIST_OF_INFORMATIONS_YOU_WILL_GET>
    </what_is_this_tool_doing?>

<when_to_call_this_tool>
1.call this tool when we know specific package name with its price or locations unless user is okay with broader search without specific prices and locations
2.when you want to put items into cart but couldn't find the url of the package, call this tool to get the url.
</when_to_call_this_tool>

<when_not_to_call_this_tool>
1.when user is asking something broadly like just package name, or location, or prices. gracefully, probe them back to collect information first. because we need search query to be specific.
2.try probing for all informations such as package name, preferred locations, and prices users might have seen on our website, if user is not sure then probe if it's okay to do broad search on just package name first.
3.when user type a name of package that is a bit ambiguos or some strange typos that is unclear, do not make a guess and probe user back something like "I'm not quite sure what is package you wanted,do you mean to ask for X? if no please specify clearer package name please?"
</when_not_to_call_this_tool>

    <NOTE>
    - Sometimes, user might ask about payment method which is not CONFIRM that they want to buy, so you can still answer with informations in <LIST_OF_INFORMATIONS_YOU_WILL_GET> thus you should still call this function.
    - Sometimes, user might ask about 'how to book?' which again this might not be a sign that they CONFIRM to book but might just interest in ways of book for making decision.
    </NOTE>
    """,
    "input_schema" : {
        "type" : "object",
        "properties" : {
            "search_keyword" : {
                "type" : "string",
                "description" : f"""
                1.Extract a search keyword in chat conversation in following schema : name of package or service, location, clinic/hospital name, price. location and clinic/hospital are optional if they're not present in chats.
                2.If the conversation was talking about different package and location, picked the recent one.
                3.Output only the search_keyword without anything else

                See the following examples:

                <example_1> 
                user : สนใจบริการผ่าตัดกระจกตาแก้สายตาสั้นค่ะ ใกล้ๆสยามม ถ้าเป็นไปได้อยากได้ของรพ.ศิริราชค่ะ ราคา 1,000บาท


                rewritten_query : บริการผ่าตัดกระจกตาแก้สายตาสั้น สยาม โรงพยาบาลศิริราช ราคา 1,000 บาท
                </example_1>

                <example_2>
                user : สนใจบริการผ่าตัดกระจกตาแก้สายตาสั้นค่ะ ใกล้ๆสยามม ถ้าเป็นไปได้อยากได้ของรพ.ศิริราชค่ะ ราคา 1,000บาท
                assistant : ค่าาตอนนี้เรามีโปรเลสิกนะคะ เข้าวัดสายตาฟรีค่ะ ราคาเริ่มต้น....blah blah blah
                user : อ๋อขอบคุณมากค่าา ไว้ขอลองตัดสินใจก่อนนะคะ
                assistant : ได้เลยค่ะคุณลูกค้า หรือสนใจลองปรึกษาแพทย์ก่อนได้นะคะคุณลูกค้า
                user : ได้ค่ะ เดี๋ยวไว้ยังไงติดต่ออีกทีนะคะ ว่าแต่มีบริการรีเทนเนอร์ใสแถวปิ่นเกล้ามั้ยคะ?

                rewritten_query = "รีเทนเนอร์ใส ปิ่นเกล้า"
                </example_2>

                <example_3 not sure>
                user : สอบถามค่ะ
                </example_3 not sure>

                If it's abiguos and hard to get the search_keyword, just output <NOT_SURE> like in <example_3 not sure>
                """
            },
            "preferred_area" : {
                "type" : "string",
                "description" : f""" 
                parse the preferred area specified in the chat conversation. just put the area and nothing else. here are the examples :

                <example_1>
                user : สวัสดีค่ะ
                assistant : สวัสดีค่ะยินดีต้อนรับเข้าสู่ Hdmall นะคะคุณลูกค้าสนใจบริการอะไรเป็นพิเศษรึเปล่าคะ จิ๊บยินดีช่วยค่าา :emojis:
                user : สนใจบริการตรวจคัดกรองมะเร็งเต้านมค่าา อยู่แถวบางแคค่ะ

                preferred_area = "บางแค"
                </example_1>

                <example_2>
                user : สวัสดีค่ะ สนใจดัดฟันใสค่ะ
                assistant : ค่าคุณลูกค้าตอนนี้เรามีโปรโมชั้น Invisalign นะคะ blah blah blah
                user : สะดวกแถวมักกะสันค่ะ
                
                preferred_area = "มักกะสัน"

                </example_2>

                if there's no location or area specified in chat conversation, then just put <UNKNOWN> for this
                """
            },
            "radius" : {
                "type" : "integer",
                "description" : "radius from preferred_area, retrieval will only retrieve packages within this radius from preferred_area if specified. If user haven't provided this please leave it as <UNKNOWN>. Only provide the number for example if user says 5km then only put 5 for this."
            },
            "package_url" : {
                "type" : "string",
                "description" : "package url from chat conversation if user provided the url or from 'retrieval' with <GET_PACKAGE_METADATA>. ALWAYS output package_url if you want to call 'retrieval' with <PROVIDE_PACKAGE_INFO>"
            },
            "category_tag" : {
                "type" : "string",
                "description" : f""" 
                parse the category tag specified in the chat conversation. just put the category tag and nothing else. here are the examples :
                
                here is the list of category tags with the corresponding url of the category page and packages in that category.
   <category_tag_list> 

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
    
                <example_1>
                user : สวัสดีค่ะ
                assistant : สวัสดีค่ะยินดีต้อนรับเข้าสู่ Hdmall นะคะคุณลูกค้าสนใจบริการอะไรเป็นพิเศษรึเปล่าคะ จิ๊บยินดีช่วยค่าา :emojis:
                user : สนใจบริการตรวจคัดกรองมะเร็งเต้านมค่าา อยู่แถวบางแคค่ะ
                category_tag = "ตรวจคัดกรองมะเร็งเต้านม"

                </example_1>

                - Try to predict/guess the category tag based on the user's query first. sometimes user query will contain some highlight page url, so you can do pattern matching.
                - for "เลเซอร์กำจัดขน" and "กำจัดขนรักแร้ (Armpit Hair Removal)" there are list of packages url provided in the package_url field. please only tag theses category if user's query is about those packages in the package_url field but if user comes with just highlight url without any package url then it's okay to tag theses category.
                - If it's really not matching any categories in here then feel free to return <UNKNOWN>


                """
            },
            "reason" : {
                "type" : "string",
                "description" : "reason why you call this tool , it's either to provide information or to get package url when you want to use cart tool. always pick either <PROVIDE_PACKAGE_INFO> or <GET_PACKAGE_METADATA>."
            }
            
        },
        "required" : ["search_keyword", "preferred_area", "radius", "category_tag", "reason", "package_url"],
        "cache_control": {"type": "ephemeral"}
    }
}
    
    handover_to_cx = {
    "name" : "handover_to_cx",
    "description" :  """
    ALWAYS call this function when the <LIST_OF_INFORMATIONS_YOU_WILL_GET> in 'retrieval' tool doesn't seem to be able to answer user's query. OR ALWAYS call this function when last couple turns of 'assistant' role seems to not be able to handle user query with good UX.
    <instruction>This function is used to seamlessly transfer the current conversation to a live
                customer support agent/human/someone when the user's message indicates the following :
                    1. If the user wants to talk to a salesperson to buy something, call the 'handover_to_cx' function
                    2. If the user wants something that you cannot provide, call the 'handover_to_cx' function like "อยากคุยกับหมอได้มั้ยคะ" since you're not doctor
                    3. If the user is ready to purchase a package/service
                Caution : There is a nuance when the user says "I want..."/"Im looking for..". 
                Based on the chat history, if the user says they want to purchase the package then call this function. 
                If they are simply curious and say something like "I want/looking for a health checkup/treatment", 
                DO NOT call this as its still too general and you can still gather more information.
                </instruction>
                """,
    "input_schema" : {
        "type":"object",
        "properties": {
            "package_name" : {
                "type" : "string",
                "description" : f"""
                answer this part with just the package_name that user wants to buy, no need other response just the full name of package as you see on RETRIEVED_PACKAGE or chat history of users
                """
            },
            "package_category" : {
                "type" : "string",
                "description" : f""" 
                
                """
            },
            "package_location" : {
                "type" : "string",
                "description" : f"""
                answer this part with just the package_location that user wants to buy, no need other response just the full name of package location/places as you see on RETRIEVED_PACKAGE or chat history of users
                """
            },
            "price_and_budget" : {
                "type" : "string",
                "description" : f"""
                answer this part with just the prices or budget that user/assitant were discussed OR agreed during the chat history or the one from RETRIEVED_PACKAGE for example :
                
                1890.0 Baht
                
                """
            }
        },
        "required" : ["package_name", "package_category","package_location", "price_and_budget"]
    }
    }

    handover_to_bk = {
    "name" : "handover_to_bk",
    "description" : """
    <information_needed_to_call_this_tool>
    1.full name and last name
    2.prefer booking date
    3.mobile phone
    </information_needed_to_call_this_tool>
    1.This function will handover to booking agent who can take care of scheduling and also re-scheduling. when user ask for booking/schedule/reschedule, ALWAYS kindly ask them back the first and last name,date they prefer, and mobile phone number first before calling this function. 
    2.when all 3 of informations needed to call this tool are present then call this tool.
                """,
    "input_schema" : {
        "type":"object",
        "properties": {
            "full_name_last_name" : {
                "type" : "string",
                "description" : f"""
                Full name and last name that provided by user.

                """
            },
            "booking_date" : {
                "type" : "string",
                "description" : f"""
                booking date or rescehdule date provided by user.

                """
            },
            "mobile_phone" : {
                "type" : "string",
                "description" : f"""
                mobile phone number provided by either user themselves or mobile app template message.
                

                """
            },
        },
        "required" : ["full_name_last_name", "booking_date", "mobile_phone"]
    }
    }
    
    handover_asap = {
    "name" : "handover_asap",
    "description" : """
    <Instruction>We will give you set of topics/subjects that are very sensitive and we want you to call this function right away when user starts to ask about that
    topic or subject</Instruction>
                 <set_of_topics/subjects>
                    <subject_1>Lasik for eyes</subject_1>
                    <subject_2>ReLEx for eyes</subject_2>
                    <subject_3>HPV vaccines</subject_3>
                    <subject_4>Food Intolerance / Hidden Food allergy Testing</subject_4>
                    <subject_6>Veneer for teeth</subject_6>
                    <subject_7>General Health Checkup / ตรวจสุขภาพ</subject_7>
                </set_of_topics/subjects>
    
    * Only call this functions when user query falls into these specific packages, DO NOT call this functions when user query is about similar packages like for example clear retainer might be similar to veneer but they're aren't exactly the same so don't call this. *
    - Do not make any guess, if user is unclear about what they want, just say you don't know and ask them to be more specific.
    
                """,
    "input_schema" : {
        "type":"object",
        "properties": {
            "package_name" : {
                "type" : "string",
                "description" : f"""
                            One of the package names that triggered this function. 
                            if the package name is/about either Lasik/ReLEx, return "Lasik"
                            if the package name is/about HPV vaccines, return "HPV Vaccine"
                            if the package name is/about Food Intolerance, return "Food Intolerance"
                            if the package name is/about Veneer, return "Veneer"
                            if the package name is/about Health Checkup, return "Health Checkup"
                """
            }
        },
        "required" : ["package_name"]
    }
    }

    cart = {
    "name" : "cart",
    "description" : """
  <instruction>
  This is a cart function with 5 available actions:
  1. create_cart : create a new shopping cart
  2. delete_cart : delete a shopping cart
  3. add_item_to_cart : add an item to the shopping cart
  4. delete_item_from_cart : delete an item from the shopping cart
  5. view_cart : view the items in the shopping cart
  6. create_order : create an order from the shopping cart for payment url

  where each action has different parameters.
  1. create_cart has no parameters.
  2. delete_cart has 1 parameter :
  - cart_id
  3. add_item_to_cart has 2 parameters:
  - package_url
  - cart_id
  4. delete_item_from_cart has 2 parameters:
  - package_url
  - cart_id
  5. view_cart has 1 parameter:
  - cart_id
  6. create_order has 1 parameter:
  - cart_id


  </instruction>
                """,
    "input_schema" : {
        "type":"object",
        "properties": {
            "action" : {
                "type" : "string",
                "description" : f"""
                The action to perform. please select only from the following actions:
                - "create_cart"
                - "delete_cart"
                - "add_item_to_cart"
                - "delete_item_from_cart"
                - "view_cart"
                - "create_order"
                """
            },
            "cart_id" : {
                "type" : "string",
                "description" : "The id of the cart to perform the action on. if the action you selected doesn't require a cart id, please leave this as <NULL>."
            },
            "package_url" : {
                "type" : "string",
                "description" : "The url of the package to perform the action on. if the action you selected doesn't require a package url, please leave this as <NULL>."
            }
        },
        "required" : ["action", "cart_id", "package_url"]
    }
    }

    ask_hospital = {
    "name" : "ask_hospital",
    "description" : """
    This tool allows you to ask specific questions about a hospital or medical package to get detailed information.
    Use this tool when you need to get specific information about a medical service, procedure, or package that requires direct inquiry to the hospital or medical provider.
    Also, use this tool when you need to get booking time-slot from hospital/clinic
                """,
    "input_schema" : {
        "type":"object",
        "properties": {
            "question" : {
                "type" : "string",
                "description" : "The specific question you want to ask about the hospital or medical package. This could me specific medical FAQ or booking time-slot. ALWAYS comfirm this with user before calling this tool. we don't want to send wrong question to hospital/clinic"
            },
            "package_url" : {
                "type" : "string",
                "description" : "The URL of the package or service you are asking about. This is the url of the package that you want to ask about. ALWAYS confirm this with user before calling this tool. we don't want to send wrong package url to hospital/clinic"
            }
        },
        "required" : ["question", "package_url"]
    }
    }

    web_recommendation = {
    "name" : "web_recommendation",
    "description" : """
a web recommendation tool that can recommend web url based on the query and type. You can use this tool multiple times to get multiple web pages from different types.
                """,
    "input_schema" : {
        "type":"object",
        "properties": {
            "query" : {
                "type" : "string",
                "description" : "extract search query from user's question, and use this query to search for web pages"
            },
            "type" : {
                "type" : "string",
                "description" : """
                please select only from the following types:
                - "hl" for highlights pages
                - "brand" for brand pages
                - "cat" for category pages
                - "tag" for tag pages
                """
            }
        },
        "required" : ["query", "type"],
        "cache_control": {"type": "ephemeral"}
        
        

    }
    }















   