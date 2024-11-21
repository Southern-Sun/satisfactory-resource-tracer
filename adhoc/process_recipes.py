import csv
import json

FILE = r"C:\Users\John\Downloads\FE6515's Satisfactory Spreadsheet - Recipe.csv"

def log_recipe(*args) -> dict:
    # Unpack Args
    name, machine, tier, time, per_minute = args[1:6]
    peak_power = args[18]
    per_minute = float(per_minute)

    inputs = []
    for part, qty in zip(args[6:14:2], args[7:14:2]):
        if not part:
            break
        qty = float(qty)
        inputs.append({
            "name": part,
            "quantity": qty,
            "raw_quantity": float(qty * per_minute)
        })

    outputs = []
    for part, qty in zip(args[14:18:2], args[15:18:2]):
        if not part:
            break
        qty = float(qty)
        outputs.append({
            "name": part,
            "quantity": qty,
            "raw_quantity": qty * per_minute
        })

    return {
        "name": name,
        "machine": machine,
        "time": float(time),
        "energy": int(peak_power),
        "inputs": inputs,
        "outputs": outputs
    }  


all_recipes = []
with open(FILE, "r") as f:
    reader = csv.reader(f)
    # Skip header
    next(reader)

    for data in reader:
        all_recipes.append(log_recipe(*data))

with open("model/all_recipes.json", "w") as f:
    json.dump(all_recipes, f, indent=4)
