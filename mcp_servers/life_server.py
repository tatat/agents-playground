"""Life domain MCP server: cooking, health, fitness."""

from typing import Any

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Life")

# === Cooking ===


@mcp.tool(name="cooking__search_recipes")
def search_recipes(query: str, cuisine: str = "any") -> dict[str, Any]:
    """Search for recipes by ingredients or dish name.

    Args:
        query: Search query (ingredients or dish name).
        cuisine: Cuisine type filter (e.g., japanese, italian, any).

    Returns: {"recipes": [{"name": str, "time": str, "difficulty": str}]}
    """
    recipes = [
        {"name": f"{query} stir-fry", "time": "20 min", "difficulty": "easy"},
        {"name": f"Baked {query}", "time": "45 min", "difficulty": "medium"},
        {"name": f"{query} soup", "time": "30 min", "difficulty": "easy"},
    ]
    return {"recipes": recipes, "cuisine": cuisine}


@mcp.tool(name="cooking__calculate_calories")
def calculate_calories(food: str, grams: int) -> dict[str, Any]:
    """Calculate calories for a food item.

    Args:
        food: Name of the food.
        grams: Amount in grams.

    Returns: {"food": str, "grams": int, "calories": int}
    """
    cal_per_gram = hash(food) % 3 + 1
    return {"food": food, "grams": grams, "calories": grams * cal_per_gram}


@mcp.tool(name="cooking__get_nutrition")
def get_nutrition(food: str) -> dict[str, Any]:
    """Get nutrition information for a food.

    Args:
        food: Name of the food.

    Returns: {"food": str, "protein": int, "carbs": int, "fat": int, "fiber": int}
    """
    return {"food": food, "protein": 12, "carbs": 25, "fat": 8, "fiber": 3}


@mcp.tool(name="cooking__suggest_substitutes")
def suggest_substitutes(ingredient: str) -> dict[str, Any]:
    """Suggest ingredient substitutes.

    Args:
        ingredient: Ingredient to find substitutes for.

    Returns: {"ingredient": str, "substitutes": [str]}
    """
    subs = {
        "butter": ["margarine", "coconut oil", "applesauce"],
        "egg": ["flax egg", "banana", "yogurt"],
        "milk": ["oat milk", "almond milk", "soy milk"],
    }
    return {"ingredient": ingredient, "substitutes": subs.get(ingredient.lower(), ["no substitutes found"])}


@mcp.tool(name="cooking__convert_units")
def convert_cooking_units(value: float, from_unit: str, to_unit: str) -> dict[str, Any]:
    """Convert cooking measurement units.

    Args:
        value: Numeric value to convert.
        from_unit: Source unit (cup, tbsp, tsp, ml, oz, g).
        to_unit: Target unit.

    Returns: {"value": float, "from": str, "to": str, "result": float}
    """
    to_ml = {"cup": 240, "tbsp": 15, "tsp": 5, "ml": 1, "oz": 30, "g": 1}
    base = value * to_ml.get(from_unit, 1)
    result = base / to_ml.get(to_unit, 1)
    return {"value": value, "from": from_unit, "to": to_unit, "result": round(result, 2)}


# === Health ===


@mcp.tool(name="health__log_steps")
def log_steps(steps: int, date: str = "today") -> dict[str, Any]:
    """Log daily step count.

    Args:
        steps: Number of steps.
        date: Date for the log entry.

    Returns: {"logged": True, "steps": int, "date": str, "goal_progress": str}
    """
    goal = 10000
    progress = min(100, int(steps / goal * 100))
    return {"logged": True, "steps": steps, "date": date, "goal_progress": f"{progress}%"}


@mcp.tool(name="health__log_sleep")
def log_sleep(hours: float, quality: str = "good") -> dict[str, Any]:
    """Track sleep duration and quality.

    Args:
        hours: Hours of sleep.
        quality: Sleep quality (poor, fair, good, excellent).

    Returns: {"logged": True, "hours": float, "quality": str, "recommendation": str}
    """
    rec = "Great job!" if hours >= 7 else "Try to get more sleep"
    return {"logged": True, "hours": hours, "quality": quality, "recommendation": rec}


@mcp.tool(name="health__log_water")
def log_water(glasses: int) -> dict[str, Any]:
    """Log water intake.

    Args:
        glasses: Number of glasses (250ml each).

    Returns: {"logged": True, "glasses": int, "ml": int, "goal_progress": str}
    """
    ml = glasses * 250
    goal = 2000
    progress = min(100, int(ml / goal * 100))
    return {"logged": True, "glasses": glasses, "ml": ml, "goal_progress": f"{progress}%"}


@mcp.tool(name="health__log_weight")
def log_weight(kg: float, date: str = "today") -> dict[str, Any]:
    """Log body weight.

    Args:
        kg: Weight in kilograms.
        date: Date for the log entry.

    Returns: {"logged": True, "kg": float, "date": str}
    """
    return {"logged": True, "kg": kg, "date": date}


@mcp.tool(name="health__get_summary")
def get_health_summary(period: str = "week") -> dict[str, Any]:
    """Get health summary for a period.

    Args:
        period: Time period (day, week, month).

    Returns: {"period": str, "avg_steps": int, "avg_sleep": float, "avg_water": int}
    """
    return {"period": period, "avg_steps": 7500, "avg_sleep": 7.2, "avg_water": 6}


@mcp.tool(name="health__set_medication_reminder")
def set_medication_reminder(medication: str, time: str, frequency: str = "daily") -> dict[str, Any]:
    """Set a medication reminder.

    Args:
        medication: Name of medication.
        time: Time for reminder (HH:MM).
        frequency: How often (daily, twice_daily, weekly).

    Returns: {"set": True, "medication": str, "time": str, "frequency": str}
    """
    return {"set": True, "medication": medication, "time": time, "frequency": frequency}


@mcp.tool(name="health__calculate_bmi")
def calculate_bmi(weight_kg: float, height_cm: float) -> dict[str, Any]:
    """Calculate Body Mass Index.

    Args:
        weight_kg: Weight in kilograms.
        height_cm: Height in centimeters.

    Returns: {"bmi": float, "category": str}
    """
    height_m = height_cm / 100
    bmi = weight_kg / (height_m * height_m)
    if bmi < 18.5:
        category = "Underweight"
    elif bmi < 25:
        category = "Normal"
    elif bmi < 30:
        category = "Overweight"
    else:
        category = "Obese"
    return {"bmi": round(bmi, 1), "category": category}


if __name__ == "__main__":
    mcp.run(transport="stdio")
