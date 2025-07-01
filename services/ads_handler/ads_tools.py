class AdsTools:
    def __init__(self):
        self.extraction = {
            "name" : "extraction",
            "description" :"""
            This tool is used to extract the main package/service that will be helpful to user. Think and analyze the user's query and extract the main package/service that will be helpful to user.
                """,
    "input_schema" : {
        "type":"object",
        "properties": {
            "search_query" : {
                "type" : "string",
                "description" : f"""
                The main package/service that will be helpful to user.
                """
            },
            "location" : {
                "type" : "string",
                "description" : "The location of the package/service that will be helpful to user. leave this to <UNKNOWN> if none"
            },
            "category_tag" : {
                "type" : "string",
                "description" : """The cateogry tag of the package/service that will be helpful to user. here's the list of catageory tag we have not that u can put <UNKOWN> if none of these are related.
                <category_tag_list> 

    <category index=1>
      <cat_name>ตรวจภูมิแพ้และภาวะแพ้ (Allergy Test)</cat_name>
      <hl_url>https://hdmall.co.th/highlight/allergy-test</hl_url>
    </category index=1>
    
    <category index=2>
      <cat_name>ตรวจตับ (Liver Function Test)</cat_name>
      <hl_url>https://hdmall.co.th/highlight/liver-checkup-oneprice</hl_url>
    </category index=2>
    
    <category index=3>
      <cat_name>ตรวจระดับฮอร์โมน (Hormone Test)</cat_name>
      <hl_url>https://hdmall.co.th/highlight/hormone-test-hdmall-plus</hl_url>
    </category index=3>
    
    <category index=5>
      <cat_name>ลดเหงื่อ ลดกลิ่นตัว</cat_name>
      <hl_url>https://hdmall.co.th/highlight/armpit-botulinum-toxin-program</hl_url>
    </category index=5>
    
    <category index=6>
      <cat_name>ฉีด Botulinum Toxin</cat_name>
      <hl_url>https://hdmall.co.th/highlight/botox-program</hl_url>
    </category index=6>
    
    <category index=7>
      <cat_name>ทําดีท็อกซ์ (Detox)</cat_name>
      <hl_url>https://hdmall.co.th/highlight/colon-hydrotherapy</hl_url>
    </category index=7>
    
    <category index=8>
      <cat_name>ตรวจ รักษาไทรอยด์</cat_name>
      <hl_url>https://hdmall.co.th/highlight/thyroid-screening-oneprice</hl_url>
    </category index=8>
    
    <category index=9>
      <cat_name>ฉีดวัคซีน HPV (HPV Vaccine)</cat_name>
      <hl_url>https://hdmall.co.th/highlight/msd-hpv-vaccine</hl_url>
    </category index=9>
    
    <category index=10>
      <cat_name>ตรวจกระดูก</cat_name>
      <hl_url>https://hdmall.co.th/highlight/osteoporosis</hl_url>
    </category index=10>
    
    <category index=12>
      <cat_name>ตรวจก่อนแต่งงาน (Pre-Marriage Checkup)</cat_name>
      <hl_url>https://hdmall.co.th/highlight/prepregnancy</hl_url>
    </category index=12>
    
    <category index=14>
      <cat_name>จี้ไฝ กระ และรอยปาน</cat_name>
      <hl_url>https://hdmall.co.th/highlight/co2-laser-2025</hl_url>
    </category index=14>
    
    <category index=15>
      <cat_name>ฉีดวัคซีนไข้หวัดใหญ่ (Influenza Vaccine)</cat_name>
      <hl_url>https://hdmall.co.th/highlight/influenza-dengue-vaccine</hl_url>
    </category index=15>
    
    <category index=16>
      <cat_name>ทำรีเทนเนอร์แบบลวด (Hawley Retainer)</cat_name>
      <hl_url>https://hdmall.co.th/highlight/retainer-one-price</hl_url>
    </category index=16>
    
    <category index=17>
      <cat_name>อุดฟัน (Dental Filling)</cat_name>
      <hl_url>https://hdmall.co.th/highlight/dental-filling</hl_url>
    </category index=17>
    
    <category index=18>
      <cat_name>ถอนหรือผ่าฟันคุด</cat_name>
      <hl_url>https://hdmall.co.th/highlight/wisdom-teeth-test</hl_url>
    </category index=18>
    
    <category index=20>
      <cat_name>ทำรีเทนเนอร์ใส (Clear Retainer)</cat_name>
      <hl_url>https://hdmall.co.th/highlight/retainer-one-price</hl_url>
    </category index=20>
    
    <category index=21>
      <cat_name>ตรวจมะเร็งสำหรับผู้หญิง</cat_name>
      <hl_url>https://hdmall.co.th/highlight/women_cancer-hl</hl_url>
    </category index=21>
    
    <category index=22>
      <cat_name>รักษาสิว (Acne Treatment)</cat_name>
      <hl_url>https://hdmall.co.th/highlight/acne-program</hl_url>
    </category index=22>
    
    <category index=23>
      <cat_name>โปรแกรมตรวจสุขภาพ (Health Checkup)</cat_name>
      <hl_url>https://hdmall.co.th/highlight/health-checkup-oneprice</hl_url>
    </category index=23>
    
    <category index=24>
      <cat_name>ตรวจการนอน (Sleep Test)</cat_name>
      <hl_url>https://hdmall.co.th/highlight/sleep-test</hl_url>
    </category index=24>
    
    <category index=26>
      <cat_name>รักษาหลุมสิว ลดรอยสิว</cat_name>
      <hl_url>https://hdmall.co.th/highlight/acne-scars</hl_url>
    </category index=26>
    
    <category index=27>
      <cat_name>กำจัดขนรักแร้ (Armpit Hair Removal)</cat_name>
      <hl_url>https://hdmall.co.th/highlight/armpit-hair-removal-oneprice</hl_url>
    </category index=27>
    
    <category index=28>
      <cat_name>รักษารอยแตกลาย รอยคล้ำ (Stretch Marks Treatment)</cat_name>
      <hl_url>https://hdmall.co.th/highlight/dark-marks-laser</hl_url>
    </category index=28>
    
    <category index=29>
      <cat_name>ฉีดวัคซีนไข้เลือดออก</cat_name>
      <hl_url>https://hdmall.co.th/highlight/qdenga-vaccine</hl_url>
    </category index=29>
    
    <category index=30>
      <cat_name>ตรวจภูมิแพ้อาหารแฝง (Food Intolerance Test)</cat_name>
      <hl_url>https://hdmall.co.th/highlight/food-intolerance-test</hl_url>
    </category index=30>
    
    <category index=31>
      <cat_name>ตรวจโรคติดต่อทางเพศสัมพันธ์ (STD)</cat_name>
      <hl_url>https://hdmall.co.th/highlight/std-check-sure</hl_url>
    </category index=31>
    
    <category index=32>
      <cat_name>ทำ Morpheus 8</cat_name>
      <hl_url>https://hdmall.co.th/highlight/morpheus-8</hl_url>
    </category index=32>
    
    <category index=33>
      <cat_name>กายภาพบำบัดออฟฟิศซินโดรม (Physical Therapy Office Syndrome)</cat_name>
      <hl_url>https://hdmall.co.th/highlight/office-syndrome</hl_url>
    </category index=33>
    
    <category index=34>
      <cat_name>ทำอัลเทอร์รา (Ulthera)</cat_name>
      <hl_url>https://hdmall.co.th/highlight/ultherapy</hl_url>
    </category index=34>
    
    <category index=35>
      <cat_name>ทำ Pico Laser</cat_name>
      <hl_url>https://hdmall.co.th/highlight/pico-laser-2025</hl_url>
    </category index=35>
    
    <category index=39>
      <cat_name>ฟอกสีฟัน (Teeth Whitening)</cat_name>
      <hl_url>https://hdmall.co.th/highlight/teeth-whitening</hl_url>
    </category index=39>
    
    <category index=41>
      <cat_name>รักษาแผลเป็นคีลอยด์ (keloid treatment)</cat_name>
      <hl_url>https://hdmall.co.th/highlight/keloid</hl_url>
    </category index=41>
    </category_tag_list>
                  """
            }
        },
        "required" : ["search_query", "location", "category_tag"]
    }
    }