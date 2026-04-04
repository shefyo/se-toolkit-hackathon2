import json
import os
import re
from difflib import get_close_matches
from typing import List, Dict
from openai import OpenAI

LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-3.5-turbo")

# ==================== ALLOWED CATEGORIES ====================

VALID_CATEGORIES = [
    "food", "transport", "entertainment",
    "shopping", "utilities", "health", "travel", "other"
]

# ==================== KEYWORD MAPPINGS ====================
# These override the LLM — rule-based correction is ALWAYS applied.

CATEGORY_KEYWORDS = {
    "food": [
        "coffee", "pizza", "lunch", "dinner", "breakfast", "burger", "snack",
        "cake", "beer", "wine", "drink", "meal", "restaurant", "cafe", "bakery",
        "chips", "crisps", "grocery", "groceries", "milk", "bread", "cheese",
        "pasta", "rice", "chicken", "meat", "fish", "sushi", "salad", "soup",
        "sandwich", "taco", "steak", "fries", "ice cream", "donut", "cookie",
        "potato", "tomato", "fruit", "vegetable", "apple", "banana", "egg",
        "butter", "yogurt", "cereal", "water", "juice", "soda", "tea"
    ],
    "transport": [
        "taxi", "uber", "bolt", "bus", "train", "metro", "subway", "fuel",
        "gas", "petrol", "parking", "toll", "tram", "bike rental", "scooter",
        "airfare", "flight", "flight ticket"
    ],
    "entertainment": [
        "cinema", "movie", "ticket", "concert", "netflix", "spotify", "game",
        "games", "gaming", "theater", "theatre", "museum", "zoo", "amusement",
        "streaming", "disney", "hulu", "youtube", "twitch", "book", "magazine",
        "comic", "novel", "event", "festival", "club", "bar", "pub", "bowling",
        "karaoke", "arcade", "subscription"
    ],
    "shopping": [
        "clothes", "clothing", "shoes", "sneakers", "electronics", "phone",
        "laptop", "tablet", "headphones", "charger", "case", "gadget", "shirt",
        "pants", "jeans", "dress", "jacket", "coat", "hat", "bag", "backpack",
        "watch", "jewelry", "perfume", "cosmetics", "makeup", "furniture",
        "decor", "appliance", "tv", "monitor", "keyboard", "mouse"
    ],
    "utilities": [
        "electricity", "water", "internet", "wifi", "phone bill", "rent",
        "heating", "gas bill", "sewage", "trash", "garbage", "utility",
        "cloud storage", "icloud", "google one"
    ],
    "health": [
        "medicine", "doctor", "pharmacy", "hospital", "gym", "vitamin",
        "dentist", "therapy", "massage", "insurance", "clinic", "prescription",
        "bandage", "painkiller", "supplement", "protein"
    ],
    "travel": [
        "hotel", "hostel", "airbnb", "accommodation", "luggage", "visa",
        "passport", "tour", "excursion", "cruise", "resort", "camping",
        "suitcase", "booking", "reservation"
    ]
}

# Order matters: categories checked first win on ambiguous keywords.
# "ticket" defaults to entertainment (cinema, concert) over transport.
# "subscription" is checked under entertainment (netflix, spotify).
CATEGORY_CHECK_ORDER = [
    "entertainment",
    "food",
    "transport",
    "travel",
    "shopping",
    "health",
    "utilities",
    "other",
]

# ==================== TYPO CORRECTION MAP ====================
# Common typos → correct spelling

TYPO_CORRECTIONS = {
    "luch": "lunch",
    "cinma": "cinema",
    "cofee": "coffee",
    "coffe": "coffee",
    "piza": "pizza",
    "pizaa": "pizza",
    "restaraunt": "restaurant",
    "resturant": "restaurant",
    "restarant": "restaurant",
    "bargur": "burger",
    "sushi": "sushi",
    "tickt": "ticket",
    "ticke": "ticket",
    "transpor": "transport",
    "entertainmant": "entertainment",
    "entartainment": "entertainment",
    "cloth": "clothes",
    "clothe": "clothes",
    "shooes": "shoes",
    "elecronics": "electronics",
    "medicin": "medicine",
    "farmacy": "pharmacy",
    "pharmcy": "pharmacy",
    "utilites": "utilities",
    "grocerie": "groceries",
    "bakerry": "bakery",
}


# ==================== MAIN PARSING FUNCTION ====================

SYSTEM_PROMPT = """You are an expense extraction assistant.
Extract all expenses from the user's text and return ONLY a valid JSON array.
Each expense must have:
- item: the name of the expense (fix typos, use common sense)
- amount: the numeric amount (number only, no currency symbols)
- category: EXACTLY one of: food, transport, entertainment, shopping, utilities, health, travel, other

Category rules:
- food = meals, drinks, groceries (coffee, pizza, chips, lunch, groceries)
- transport = taxi, bus, train, fuel, gas, parking
- entertainment = cinema, movies, games, streaming, tickets for events
- shopping = clothes, electronics, gadgets, accessories
- utilities = rent, electricity, internet, bills
- health = medicine, doctor, gym, pharmacy
- travel = hotel, hostel, luggage, tours, accommodation

Return ONLY the JSON array, nothing else. If no expenses found, return [].

Example output:
[{"item": "coffee", "amount": 5, "category": "food"}, {"item": "cinema ticket", "amount": 10, "category": "entertainment"}]
"""


def parse_expenses_with_llm(text: str) -> List[Dict]:
    """Parse expenses from text using LLM, then correct categories with rules."""
    if not LLM_API_KEY:
        expenses = _fallback_parse(text)
    else:
        client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)

        try:
            response = client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": text}
                ],
                temperature=0.1,
                max_tokens=500
            )

            content = response.choices[0].message.content.strip()

            # Extract JSON from response (handle markdown code blocks)
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]

            raw_expenses = json.loads(content.strip())
            if not isinstance(raw_expenses, list):
                raw_expenses = []

            # Normalize raw expenses
            expenses = []
            for exp in raw_expenses:
                if not isinstance(exp, dict):
                    continue
                item = str(exp.get("item", "")).strip()
                try:
                    amount = float(exp.get("amount", 0))
                except (ValueError, TypeError):
                    continue
                category = str(exp.get("category", "other")).strip().lower()

                if not item or amount <= 0:
                    continue

                expenses.append({
                    "item": item,
                    "amount": amount,
                    "category": category
                })

        except Exception as e:
            print(f"LLM error: {e}, falling back to simple parsing")
            expenses = _fallback_parse(text)

    # ==================== CRITICAL: Rule-based category correction ====================
    # ALWAYS override LLM output with keyword-based rules
    for expense in expenses:
        expense["category"] = correct_category(expense["item"], expense["category"])

    return expenses


# ==================== CATEGORY CORRECTION (RULE-BASED OVERRIDE) ====================

def correct_category(item: str, llm_category: str = "other") -> str:
    """
    Correct the category using keyword matching.
    Rules ALWAYS override the LLM.

    Args:
        item: the expense item name
        llm_category: the category assigned by the LLM (used as fallback)
    Returns:
        corrected category (one of VALID_CATEGORIES)
    """
    item_lower = item.lower().strip()

    # Step 1: Fix typos in item name
    corrected_item = fix_typos(item_lower)

    # Step 2: Try exact keyword match in priority order.
    # When multiple categories match, pick the one with the longest matching keyword
    # (more specific match wins).
    # EXCEPTION: if the item exactly equals a keyword, that category wins immediately
    # (prevents substring collisions like "ticket" matching "flight ticket").
    best_category = None
    best_keyword_len = 0

    for category in CATEGORY_CHECK_ORDER:
        if category == "other":
            continue
        keywords = CATEGORY_KEYWORDS.get(category, [])
        for keyword in keywords:
            # Exact match on the full item — highest priority
            if corrected_item == keyword:
                return category
            # Substring match
            if keyword in corrected_item or corrected_item in keyword:
                kw_len = len(keyword)
                if kw_len > best_keyword_len:
                    best_keyword_len = kw_len
                    best_category = category

    if best_category:
        return best_category

    # Step 3: Fuzzy match — find closest keyword
    all_keywords = []
    keyword_to_category = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            all_keywords.append(kw)
            keyword_to_category[kw] = category

    close = get_close_matches(corrected_item, all_keywords, n=1, cutoff=0.7)
    if close:
        return keyword_to_category[close[0]]

    # Step 4: Validate LLM fallback — if invalid, set to "other"
    if llm_category in VALID_CATEGORIES:
        return llm_category

    return "other"


# ==================== TYPO CORRECTION ====================

def fix_typos(item: str) -> str:
    """Fix common typos in item names using explicit map + fuzzy matching."""
    item_lower = item.lower().strip()

    # Step 1: Check explicit typo map
    if item_lower in TYPO_CORRECTIONS:
        return TYPO_CORRECTIONS[item_lower]

    # Step 2: Fuzzy match against all known keywords
    all_known = list(TYPO_CORRECTIONS.values())
    for keywords in CATEGORY_KEYWORDS.values():
        all_known.extend(keywords)

    close = get_close_matches(item_lower, all_known, n=1, cutoff=0.7)
    if close:
        return close[0]

    return item_lower


# ==================== FALLBACK PARSER (no LLM) ====================

def _fallback_parse(text: str) -> List[Dict]:
    """Simple fallback parser that extracts items with amounts using regex."""
    # Split by "and" to handle multiple expenses
    parts = re.split(r'\s+and\s+', text, flags=re.IGNORECASE)

    expenses = []
    seen_items = set()

    for part in parts:
        part = part.strip()
        # Remove common prefixes
        part = re.sub(r'\b(bought|got|paid|spent|i|we|my|our)\s+', '', part, flags=re.IGNORECASE).strip()

        # Pattern: item "for" amount
        match = re.search(r'([a-zA-Z]+(?:\s+[a-zA-Z]+)?)\s+for\s+(\d+(?:\.\d+)?)', part, re.IGNORECASE)
        if not match:
            # Pattern: amount then item
            match = re.search(r'(\d+(?:\.\d+)?)\s+(?:dollars?\s+)?(?:for\s+)?([a-zA-Z]+(?:\s+[a-zA-Z]+)?)', part, re.IGNORECASE)
            if match:
                amount, item = match.groups()
            else:
                continue
        else:
            item, amount = match.groups()

        item = item.strip().lower()
        # Skip common non-item words
        if item in ('and', 'the', 'a', 'an', 'for', 'my', 'some', 'also', 'then', 'with', 'i', 'we'):
            continue
        if item in seen_items:
            continue

        seen_items.add(item)
        expenses.append({
            "item": item,
            "amount": float(amount),
            "category": "other"  # Will be corrected by correct_category()
        })

    return expenses
