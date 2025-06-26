#hl mapping loading
import json
with open("hl_prompts/hl_mapping.json", "r") as f:
    loaded_list = json.load(f)

#test
for d in loaded_list:
    print(d['cat_name'])
    print(d['hl_url'])
    print(len(d['packages']))
    for package in d['packages']:
        print(package)
    print('--------------------------------')
    
    