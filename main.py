import requests
import json
import os
import random

# === 配置 ===
store_url = os.environ.get('store_url')
access_token = os.environ.get('store_url')
headers = {
    'Content-Type': 'application/json',
    'X-Shopify-Access-Token': access_token
}

discount_file = 'yesterday_discounts.json'
discount_rate = 0.9  # 打 85 折
products_num =8   # 随机打折的产品数量


# === Step 1: 恢复昨日打折商品 ===
if os.path.exists(discount_file):
    with open(discount_file, 'r', encoding='utf-8') as f:
        old_discounts = json.load(f)
    for item in old_discounts:
        variant_id = item['variant_id']
        original_price = item['original_price']
        update_data = {
            "variant": {
                "id": variant_id,
                "price": original_price,
                "compare_at_price": None  # 清除对比价
                
            }
        }
        resp = requests.put(
            f'{store_url}/admin/api/2023-10/variants/{variant_id}.json',
            headers=headers,
            json=update_data
        )
        if resp.status_code == 200:
            print(f"✅ 恢复 SKU {item['sku']} 的原价 {original_price}")
        else:
            print(f"❌ 恢复失败 SKU {item['sku']} - {resp.status_code}: {resp.text}")
else:
    print("昨日无折扣记录")

# === Step 2: 获取产品（前2页，每页250个）===
print("正在获取产品...")
all_products = []

page_info = None
page_count = 0
max_pages = 4

while page_count < max_pages:
    params = {
        'limit': 50,
        'fields': 'id,title,variants,tags,status,published_at',
        'page_info': None,  # 分页参数
        
    }  
        
      
        
    if page_info:
        params['page_info'] = page_info
    else:
      params['order'] = 'created_at desc'      
        
    r = requests.get(f'{store_url}/admin/api/2023-10/products.json', headers=headers, params=params)
    if r.status_code != 200:
        print(f"❌ 获取产品失败: {r.status_code}")
        print("错误详情：", r.text)
        break
    products = r.json().get('products', [])
    for p in products:
        if p.get('status') == 'active':
            all_products.append(p)
    page_count += 1
    
    if 'link' in r.headers and 'rel="next"' in r.headers['link']:
        links = r.headers['link'].split(',')
        for link in links:
            if 'rel="next"' in link:
                next_url = link[link.find('<')+1:link.find('>')]
                page_info = next_url.split('page_info=')[1].split('&')[0]
                break
    else:
        break

print(f"✅ 有效产品数量：{len(all_products)}")



#test
# for product in all_products:
#     print(f"产品标题: {product['title']}, 变体数量: {len(product['variants'])}")




# === Step 3: 随机挑选 4 个产品，下所有变体打折 ===
selected_products = random.sample(all_products, min(products_num, len(all_products)))
new_discount_log = []

for product in selected_products:
    print(f"🔸 打折产品: {product['title']}")
    for variant in product['variants']:
        variant_id = variant['id']
        old_price = float(variant['price'])
        new_price = round(old_price * discount_rate, 2)
        update_data = {
            "variant": {
                "id": variant_id,
                "price": str(new_price),
                "compare_at_price": str(old_price)  # 设置原价为对比价格
            }
        }
        resp = requests.put(
            f'{store_url}/admin/api/2023-10/variants/{variant_id}.json',
            headers=headers,
            json=update_data
        )
        if resp.status_code == 200:
            print(f"  ✅ 打折 SKU {variant['sku']}：{old_price} → {new_price}")
            new_discount_log.append({
                'variant_id': variant_id,
                'sku': variant['sku'],
                'original_price': str(old_price)
            })
        else:
            print(f"  ❌ 打折失败 SKU {variant['sku']}: {resp.status_code} - {resp.text}")

# === Step 4: 写入本地日志 ===
with open(discount_file, 'w', encoding='utf-8') as f:
    json.dump(new_discount_log, f, ensure_ascii=False, indent=2)

print("✅ 本轮打折商品记录已保存")
