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

# ==================== CATEGORY KEYWORD MAP ====================
# Comprehensive keyword lists for rule-based fallback and post-validation.

CATEGORY_KEYWORDS = {
    "food": [
        "coffee", "cafe", "lunch", "dinner", "breakfast", "pizza", "burger", "snack",
        "cake", "beer", "wine", "drink", "meal", "restaurant", "bakery",
        "chips", "crisps", "potato chips", "grocery", "groceries", "milk", "bread", "cheese",
        "pasta", "rice", "chicken", "meat", "fish", "sushi", "salad", "soup",
        "sandwich", "taco", "steak", "fries", "ice cream", "donut", "cookie",
        "potato", "tomato", "fruit", "vegetable", "apple", "banana", "egg",
        "butter", "yogurt", "cereal", "water", "juice", "soda", "tea",
        "noodles", "ramen", "kebab", "wrap", "burrito", "hotdog", "hot dog",
        "pancakes", "waffle", "muffin", "croissant", "smoothie", "latte", "cappuccino",
        "espresso", "mocha", "cocoa", "chocolate", "candy", "icecream",
    ],
    "transport": [
        "taxi", "uber", "bolt", "bus", "train", "metro", "subway", "fuel",
        "gas", "petrol", "diesel", "parking", "toll", "tram", "bike rental", "scooter",
        "car wash", "car repair", "oil change", "tire",
        "ride", "cab", "lyft", "transport", "commute",
    ],
    "entertainment": [
        "cinema", "movie", "cinema ticket", "movie ticket", "ticket", "concert",
        "netflix", "spotify", "game", "games", "gaming", "theater", "theatre",
        "museum", "zoo", "amusement", "streaming", "disney", "hulu", "youtube",
        "twitch", "book", "magazine", "comic", "novel", "event", "festival",
        "club", "bar", "pub", "bowling", "karaoke", "arcade",
        "subscription", "hbo", "prime video", "apple music",
        "show", "performance", "play", "opera", "ballet", "exhibition",
        "park entry", "theme park", "water park",
    ],
    "shopping": [
        "clothes", "clothing", "shoes", "sneakers", "electronics", "phone",
        "laptop", "tablet", "headphones", "charger", "case", "gadget", "shirt",
        "pants", "jeans", "dress", "jacket", "coat", "hat", "bag", "backpack",
        "watch", "jewelry", "perfume", "cosmetics", "makeup", "furniture",
        "decor", "appliance", "tv", "monitor", "keyboard", "mouse",
        "accessories", "socks", "underwear", "scarf", "gloves", "belt",
        "sunglasses", "umbrella", "wallet", "purse",
    ],
    "utilities": [
        "electricity", "water", "internet", "wifi", "phone bill", "rent",
        "heating", "gas bill", "sewage", "trash", "garbage", "utility",
        "cloud storage", "icloud", "google one", "mobile plan", "cell phone bill",
        "cable", "satellite", "home insurance", "maintenance",
    ],
    "health": [
        "medicine", "doctor", "pharmacy", "hospital", "gym", "vitamin",
        "dentist", "therapy", "massage", "insurance", "clinic", "prescription",
        "bandage", "painkiller", "supplement", "protein",
        "dental", "optician", "glasses", "contact lens", "checkup",
        "healthcare", "medical", "first aid",
    ],
    "travel": [
        "hotel", "hostel", "airbnb", "accommodation", "luggage", "visa",
        "passport", "tour", "excursion", "cruise", "resort", "camping",
        "suitcase", "booking", "reservation",
        "flight", "flight ticket", "airplane", "airfare",
    ],
}

# Order matters: categories checked first win on ambiguous keywords.
CATEGORY_CHECK_ORDER = [
    "entertainment",
    "food",
    "travel",
    "transport",
    "shopping",
    "health",
    "utilities",
]

# ==================== TYPO CORRECTION MAP ====================

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
    "grocries": "groceries",
    "sandwhich": "sandwich",
    "restaraunt": "restaurant",
}

# ==================== SYSTEM PROMPT ====================

SYSTEM_PROMPT = """You are an expense extraction assistant. Your job is to extract ALL expenses mentioned in the user's text and return them as a STRICT JSON array.

STRICT RULES:
1. Return ONLY a valid JSON array — no markdown, no explanation, no code blocks.
2. Extract EVERY expense mentioned — never skip items.
3. Never hallucinate expenses that aren't in the text.
4. Each expense must have exactly these fields:
   - "item": the name of the expense (lowercase, fix typos, trim spaces)
   - "amount": the numeric amount (number only, no currency symbols)
   - "category": EXACTLY one of: food, transport, entertainment, shopping, utilities, health, travel, other

CATEGORY MAPPING (use these rules):
- food = meals, drinks, groceries, snacks, restaurant orders (coffee, pizza, chips, lunch, dinner, groceries, burger, sandwich)
- transport = taxi, rideshare, bus, train, metro, fuel, gas, parking, toll (taxi, uber, bus, metro, fuel, parking)
- entertainment = cinema, movies, games, streaming, event tickets, subscriptions (cinema ticket, movie, netflix, concert, game)
- shopping = clothes, electronics, gadgets, accessories, personal items (clothes, shoes, phone, laptop, jewelry)
- utilities = rent, electricity, internet, phone bills, cloud storage (rent, electricity, internet, wifi, phone bill)
- health = medicine, doctor, gym, pharmacy, dental (pharmacy, doctor, gym, medicine)
- travel = flights, hotels, hostels, luggage, tours, accommodation (hotel, flight, airbnb, hostel)
- other = anything that clearly doesn't fit above

NORMALIZATION:
- Fix typos: "luch" → "lunch", "cinma" → "cinema", "cofee" → "coffee"
- Normalize: trim spaces, lowercase everything
- Keep multi-word items intact: "cinema ticket", "potato chips"

EXAMPLES:
Input: "I bought coffee for 5 and cinema ticket for 20"
Output: [{"item":"coffee","amount":5,"category":"food"},{"item":"cinema ticket","amount":20,"category":"entertainment"}]

Input: "coffee 5, pizza 10, cinema ticket 20"
Output: [{"item":"coffee","amount":5,"category":"food"},{"item":"pizza","amount":10,"category":"food"},{"item":"cinema ticket","amount":20,"category":"entertainment"}]

Input: "I spent 50 on groceries and 15 on taxi"
Output: [{"item":"groceries","amount":50,"category":"food"},{"item":"taxi","amount":15,"category":"transport"}]
"""


# ==================== MAIN PARSING FUNCTION ====================

def parse_expenses_with_llm(text: str) -> List[Dict]:
    """Parse expenses from text using LLM, then apply post-processing and rule-based correction."""
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
                max_tokens=1000
            )

            content = response.choices[0].message.content.strip()

            # Strip markdown code fences if present
            content = _extract_json(content)

            raw_expenses = json.loads(content)
            if not isinstance(raw_expenses, list):
                raw_expenses = []

            expenses = []
            for exp in raw_expenses:
                if not isinstance(exp, dict):
                    continue

                # Extract and validate fields
                item = str(exp.get("item", "")).strip()
                if not item:
                    continue

                try:
                    amount = float(exp.get("amount", 0))
                except (ValueError, TypeError):
                    continue
                if amount <= 0:
                    continue

                category = str(exp.get("category", "other")).strip().lower()
                if category not in VALID_CATEGORIES:
                    category = "other"

                expenses.append({
                    "item": item,
                    "amount": amount,
                    "category": category
                })

        except json.JSONDecodeError as e:
            print(f"LLM returned invalid JSON: {e}")
            expenses = _fallback_parse(text)
        except Exception as e:
            print(f"LLM error: {e}, falling back to simple parsing")
            expenses = _fallback_parse(text)

    # ==================== POST-PROCESSING ====================
    # Normalize every expense
    for expense in expenses:
        # Lowercase and trim
        expense["item"] = expense["item"].lower().strip()

        # Fix typos in item name
        expense["item"] = fix_typos(expense["item"])

        # Rule-based category correction (ALWAYS overrides LLM)
        expense["category"] = correct_category(expense["item"], expense["category"])

    # Deduplicate: merge identical items with same amount
    expenses = _deduplicate_expenses(expenses)

    return expenses


def _extract_json(content: str) -> str:
    """Extract JSON from LLM response, handling markdown code blocks and surrounding text."""
    # Try markdown code block
    match = re.search(r'```(?:json)?\s*(\[[\s\S]*?\])\s*```', content)
    if match:
        return match.group(1)

    # Try to find a JSON array anywhere in the text
    match = re.search(r'\[[\s\S]*\]', content)
    if match:
        return match.group(0)

    return content.strip()


def _deduplicate_expenses(expenses: List[Dict]) -> List[Dict]:
    """Merge duplicate expenses (same item + same amount)."""
    seen = set()
    result = []
    for exp in expenses:
        key = (exp["item"], exp["amount"])
        if key not in seen:
            seen.add(key)
            result.append(exp)
    return result


# ==================== CATEGORY CORRECTION (RULE-BASED OVERRIDE) ====================

def correct_category(item: str, llm_category: str = "other") -> str:
    """
    Correct the category using keyword matching.
    Rules ALWAYS override the LLM.

    Args:
        item: the expense item name (should already be lowercase + typo-fixed)
        llm_category: the category assigned by the LLM (used as fallback)
    Returns:
        corrected category (one of VALID_CATEGORIES)
    """
    item_lower = item.lower().strip()

    # Step 1: Exact match — item equals a keyword
    for category in CATEGORY_CHECK_ORDER:
        keywords = CATEGORY_KEYWORDS.get(category, [])
        for keyword in keywords:
            if item_lower == keyword:
                return category

    # Step 2: Substring match — pick category with longest matching keyword
    best_category = None
    best_keyword_len = 0

    for category in CATEGORY_CHECK_ORDER:
        keywords = CATEGORY_KEYWORDS.get(category, [])
        for keyword in keywords:
            if keyword in item_lower or item_lower in keyword:
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

    close = get_close_matches(item_lower, all_keywords, n=1, cutoff=0.7)
    if close:
        return keyword_to_category[close[0]]

    # Step 4: Validate LLM fallback
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
    expenses = []

    # Pattern 1: "item for amount" or "item for $amount"
    pattern1 = re.finditer(
        r'([a-zA-Z][a-zA-Z\s]*?)\s+for\s+\$?\s*(\d+(?:\.\d+)?)',
        text, re.IGNORECASE
    )
    for m in pattern1:
        item, amount = m.group(1).strip(), float(m.group(2))
        if item and amount > 0:
            expenses.append({"item": item, "amount": amount, "category": "other"})

    if expenses:
        return expenses

    # Pattern 2: "amount on/for item"
    pattern2 = re.finditer(
        r'\$?\s*(\d+(?:\.\d+)?)\s+(?:on|for)\s+([a-zA-Z][a-zA-Z\s]*?)',
        text, re.IGNORECASE
    )
    for m in pattern2:
        amount, item = float(m.group(1)), m.group(2).strip()
        if item and amount > 0:
            expenses.append({"item": item, "amount": amount, "category": "other"})

    if expenses:
        return expenses

    # Pattern 3: comma-separated "item amount" pairs
    # E.g. "coffee 5, pizza 10, cinema ticket 20"
    parts = re.split(r'[,\s]+and\s+|[,\s]+', text, flags=re.IGNORECASE)
    # Try to pair consecutive word groups with numbers
    tokens = text.replace(",", " , ").split()
    i = 0
    while i < len(tokens):
        # Look for a number followed by words, or words followed by a number
        if tokens[i].replace(".", "").isdigit():
            # Number found — look for item words nearby
            amount = float(tokens[i])
            # Collect words before or after
            item_words = []
            j = i + 1
            while j < len(tokens) and j < i + 4 and not tokens[j].replace(".", "").isdigit():
                if tokens[j] not in ("and", "the", "a", "an", "for", "on", "i", "we", "my", "spent", "paid", "bought"):
                    item_words.append(tokens[j])
                j += 1
            if item_words:
                item = " ".join(item_words).lower()
                expenses.append({"item": item, "amount": amount, "category": "other"})
            i = j
        else:
            i += 1

    return expenses
