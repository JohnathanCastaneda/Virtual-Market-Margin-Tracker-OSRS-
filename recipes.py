from tabnanny import check
import requests
import os
import time
import json
from collections import defaultdict


wiki_api = "https://oldschool.runescape.wiki/api.php"
recipe_cache = "cache/recipes.json"
cache_max_age = 60 * 60 * 24 * 14  # 14 days

class recipeLoader:
    def __init__(self, price_manager):
        self.price_manager = price_manager

    def recipe_cache(self):
        if not os.path.exists("cache"):
            os.makedirs("cache")
        
        if os.path.exists(recipe_cache):
            cache_age = time.time() - os.path.getmtime(recipe_cache)
            if cache_age < cache_max_age:
                with open(recipe_cache, "r") as f:
                    return json.load(f)
        
        print("Cache empty or expired. Fetching from Wiki...")    
        blueprints = self.load_all_recipes()
        
        if not blueprints:
            print("Failed to fetch recipes from Wiki.")
            return []
        
        with open(recipe_cache, "w") as f:
            json.dump(blueprints, f, indent=2)
        return blueprints
    
    def get_recipe(self):
        headers = {"User-Agent": "OSRS Recipe Flipper tool - personal project for myself - @johnner"}
        all_recipes = []
        offset = 0
        limit = 500
        count = 0
        
        while count < 20:
            query_str = f"bucket('recipe').select('page_name','production_json').limit({limit}).offset({offset}).run()"
            params = {
                "action": "bucket",
                "query": query_str,
                "format": "json"
            }      
            try:
                print("Fetching recipes from Wiki...")
                response = requests.get(wiki_api, params=params, headers=headers)
                response.raise_for_status()
                data_json = response.json()
                
                rows = data_json.get("bucket", [])
                
                if not rows:
                    print("Warning: Bucket returned 0 rows. Check if bucket name 'recipe' is correct.")
                    break
                
                print(f"Received response with {len(rows)} rows")
                for row in rows:
                    data = row.get("production_json")
                    if data:
                        try:
                            recipe_data = json.loads(data) if isinstance(data, str) else data
                            all_recipes.append({
                                "result_name": row.get("page_name"),
                                "data": recipe_data
                            })
                        except Exception as e:
                            continue
                
                offset += limit
                count += 1
                print(f"Batch {count} complete. Total so far: {len(all_recipes)}")
                time.sleep(0.05)
            
            except Exception as e:
                print(f"Error fetching recipes: {e}")
                break
        
        print(f"Total recipes successfully loaded: {len(all_recipes)}")
        return all_recipes
    
    def group_recipes(self, wiki_data):
        grouped = []
        
        for row in wiki_data:
            #must be a dictionary to proceed
            if not isinstance(row, dict):
                continue
            
            #Assign 'data' immediately so it is defined for all following checks
            data = row.get("data") 
            
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except Exception:
                    continue
            if not isinstance(data, dict):
                continue
            
            #get output info
            output_info = data.get("output", {}) 
            if not isinstance(output_info, dict):
                output_info = {}
                
            #Build recipe object
            result_name = output_info.get("name", row.get("result_name", "Unknown"))
            quantity = output_info.get("quantity", 1)
            try:
                output_qty = int(float(quantity))
            except Exception:
                output_qty = 1
                
            if output_qty <= 0:
                output_qty = 1
            
            current_recipe = {
                "name": result_name,
                "output": {
                    "item": result_name,
                    "qty": output_qty
                },
                "inputs": []
            }
            
            # 7. Safely handle materials list
            materials = data.get("materials", [])
            if isinstance(materials, list):
                for material in materials:
                    if isinstance(material, dict):
                        current_recipe["inputs"].append({
                            "item": material.get("name"),
                            "qty": int(float(material.get("quantity", 0)))
                        })
        
            if current_recipe["inputs"]:
                grouped.append(current_recipe)
        
        return grouped
            
        
            
    # Remove non-tradable items(both output and input) from recipes
    def remove_non_tradable(self, recipes):
        tradable_recipes = []
        for recipe in recipes:
            items = [i["item"] for i in recipe["inputs"]]
            if all(self.price_manager.is_tradable(item) for item in items):
                tradable_recipes.append(recipe)
        
        return tradable_recipes
    
    #Handles profits for each recipe
    def profits(self, recipe):
        total_cost = 0
        priced_inputs = []
        
        for input in recipe["inputs"]:
            price = self.price_manager.get_price(input["item"], price_type="low")
            if price is None:
                return None
            
            cost = price * input["qty"]
            total_cost += cost
            
            priced_inputs.append({
                "item": input["item"],
                "qty": input["qty"],
                "unit_price": price,
                "total": cost
            })
            
        output_item = recipe["output"]["item"]
        output_price = self.price_manager.get_price(output_item, price_type="high")
        if output_price is None:
            return None
            
        output_value = output_price * recipe["output"]["qty"]
            
        # Calculate tax
            
        tax = int(output_value * 0.02)
        if tax > 5000000: #OSRS GE tax cap
            tax = 5000000
                
        recipe["profit"] = output_value - total_cost - tax
        recipe["total_cost"] = total_cost
        recipe["output_value"] = output_value
        recipe["tax"] = tax
        recipe["inputs"] = priced_inputs
            
        return recipe
        
    #real time values for recipes
    def live_profits(self, recipes):
        self.price_manager.load_prices()
        profit_recipes = []
        for recipe in recipes:
            result = self.profits(recipe)
            if result:
                profit_recipes.append(result)
        return profit_recipes
    
    def load_all_recipes(self):
        raw_recipes = self.get_recipe()
        grouped_recipes = self.group_recipes(raw_recipes)
        
        best = {}
        for recipe in grouped_recipes:
            name = recipe["name"]
            if name not in best:
                best[name] = recipe
        
        return list(best.values())
        
        '''''
        raw_recipes = self.get_recipe()
        grouped_recipes = self.group_recipes(raw_recipes)
        tradable_recipes = self.remove_non_tradable(grouped_recipes)
        
        all_recipes = []
        for recipe in tradable_recipes:
            result = self.profits(recipe)
            if result:
                all_recipes.append(result)
                
        return all_recipes
        '''''