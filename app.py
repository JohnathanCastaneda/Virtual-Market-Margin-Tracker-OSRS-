import time
import requests
from flask import Flask, request, jsonify, render_template
from recipes import recipeLoader
from prices import PriceManager


app = Flask(__name__)

price_manager = PriceManager()

loader = recipeLoader(price_manager)

MAPPING_URL = "https://prices.runescape.wiki/api/v1/osrs/mapping"
PRICING_URL = "https://prices.runescape.wiki/api/v1/osrs/latest"
RECIPE_URL = "https://oldschool.runescape.wiki/api.php?action=bucket"


ITEMS = requests.get(MAPPING_URL).json()


'''''
#Calculates profit for a given recipe
def profit_recipe(recipe):
    total_cost = 0
    priced_inputs = []
    
    #Calculate total cost of ingredients
    for ingredient in recipe["ingredients"]:
        item_id = get_ItemID(ingredient["item"])
        price_data = get_Price(item_id)
        if not price_data:
            return None

        # uses the low price for cost calculation as one is not insta buying
        cost = price_data["low"] * ingredient["qty"]
        total_cost += cost

        priced_inputs.append({
            "item": ingredient["item"],
            "qty": ingredient["qty"],
            "unit_price": price_data["low"],
            "total": cost
        })

    output_id = get_ItemID(recipe["output"]["item"])
    output_price_data = get_Price(output_id)
    if output_price_data:
        tax = int((output_price_data["high"] * recipe["output"]["qty"]) * 0.02)
        if tax > 5000000:
            tax = 5000000
        output_value = output_price_data["high"] * recipe["output"]["qty"]
    else:
        return None  # Price data unavailable

    profit = output_value - total_cost - tax
    return {
        "name": recipe["name"],
        "inputs": priced_inputs,
        "output": recipe["output"],
        "total_cost": total_cost,
        "output_value": output_value,
        "profit": profit,
        "tax": tax
    }
#Acquires item id from the given request
def get_ItemID(item_Name):
    for item in ITEMS:
        if item["name"].lower() == item_Name.lower():
            return item["id"]
    return None

def get_Price(item_id):
    lookup = requests.get(PRICING_URL)
    data  = lookup.json()["data"]
    return data.get(str(item_id))
'''


@app.route('/')
@app.route('/home')
def home():
    blueprints = loader.recipe_cache()
    
    profit_list = loader.live_profits(blueprints)
    
    sorted_profits = sorted(profit_list, key=lambda x: x['profit'] if x else float('-inf'), reverse=True)
    
    return render_template('home.html', recipes=sorted_profits)
    
    '''''
    profit_recipes = [profit_recipe(recipe) for recipe in RECIPES]
    return render_template('home.html', recipes = profit_recipes)
    '''
    
    
    
#@app.route('/price')
#def price():
    item_Name = request.args.get("item", '').strip()
    
    if not item_Name:
        return jsonify({"error": "Invalid item name"}), 400
    
    item_id = get_ItemID(item_Name)
    if not item_id:
        return jsonify({"error": "Invalid Item Name"}), 404
    
    price = get_Price(item_id)
    if not price:
        return jsonify({"error": "Price unavailable"}), 404
    
    return jsonify({
        "item": item_Name,
        "high": price["high"],
        "low": price["low"]
    })


#@app.route('/NewRecipe')
#def new_recipe():
    return render_template('NewRecipe.html', title='New Recipe')
    
    
#@app.route('/search')
#def search():
    query = request.args.get('q', "").lower()
    
    if not query:
        return jsonify([])

    results = []
    for item in ITEMS:
        if item["name"].lower().startswith(query):
            results.append(item["name"])
        if len(results) == 25:
            break

    return jsonify(results)


if __name__ == "__main__":
    app.run(debug=True)