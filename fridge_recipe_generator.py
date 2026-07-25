import streamlit as st
from openai import OpenAI
import json
import os

st.set_page_config(page_title="What's in Your Fridge?", page_icon="🍳", layout="centered")
st.title("🍳 What's in Your Fridge?")
st.markdown(
    "List the ingredients you have on hand, and get 2-3 recipe ideas you can make with them. "
    "**Free to use** — no sign-up or API key needed on your end!"
)

# ---------------------------------------------------------------------------
# Groq client setup
# ---------------------------------------------------------------------------
# The developer's own free Groq API key powers this app — visitors never
# need to provide their own key. Get a free key at https://console.groq.com
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

if not GROQ_API_KEY:
    st.error(
        "⚠️ No Groq API key configured. If you're the developer running this locally, "
        "set the GROQ_API_KEY environment variable. Get a free key at "
        "[console.groq.com](https://console.groq.com/keys)."
    )
    st.stop()

client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1",
)

GROQ_MODEL = "llama-3.3-70b-versatile"


# ---------------------------------------------------------------------------
# Helper: dropdown with a fallback "type your own" option
# ---------------------------------------------------------------------------
def dropdown_or_custom(label: str, options: list, key: str) -> str:
    """
    Shows a selectbox with the given options plus an "Other (type your own)"
    choice. If that's picked, reveals a text input beneath it. Returns
    whichever value the user ended up choosing/typing.
    """
    choice = st.selectbox(label, options + ["Other (type your own)"], key=f"{key}_select")
    if choice == "Other (type your own)":
        custom = st.text_input(f"Enter your own {label.lower()}", key=f"{key}_custom")
        return custom.strip()
    return choice


# ---------------------------------------------------------------------------
# Recipe generation
# ---------------------------------------------------------------------------
def generate_recipes(preferences: dict) -> list:
    """
    Ask the LLM for 2-3 recipe ideas based on the given ingredients and
    preferences. Returns a list of dicts with title, uses_ingredients,
    extra_ingredients, approx_calories_per_serving, and steps.
    """
    system_instructions = (
        "You are a helpful, creative home cooking assistant. "
        "You always respond with a single valid JSON object and nothing else - "
        "no markdown fences, no commentary."
    )

    pref_lines = []
    for label, value in preferences.items():
        if value and str(value).strip() and str(value).lower() not in ("no preference", "any"):
            pref_lines.append(f"- {label}: {value}")
    pref_block = "\n".join(pref_lines) if pref_lines else "- No specific preferences, use your best judgment."

    prompt = f"""
The user has these ingredients on hand: {preferences.get('ingredients', '')}

Preferences to respect:
{pref_block}

Suggest 2-3 simple, realistic recipes they could make, prioritizing dishes that use
mostly what they already have. It's fine to assume basic pantry staples (salt, pepper,
oil, water) are available even if not listed. Give a reasonable estimated calorie count
per serving (it doesn't need to be exact — a sensible ballpark is fine).

Return ONLY a JSON object with this exact shape:
{{
  "recipes": [
    {{
      "title": "Recipe name",
      "uses_ingredients": ["ingredient1", "ingredient2"],
      "extra_ingredients": ["anything needed that they didn't list, besides basic staples"],
      "approx_calories_per_serving": "e.g. ~350 kcal",
      "steps": ["Step 1 text", "Step 2 text", "..."]
    }}
  ]
}}
"""

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": system_instructions},
            {"role": "user", "content": prompt},
        ],
        temperature=0.8,
    )

    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        parsed = json.loads(raw)
        return parsed.get("recipes", [])
    except json.JSONDecodeError:
        st.error("Hmm, couldn't parse a recipe from that. Try again?")
        return []


# ---------------------------------------------------------------------------
# UI — main inputs
# ---------------------------------------------------------------------------
ingredients = st.text_area(
    "What ingredients do you have?",
    placeholder="e.g. chicken breast, rice, broccoli, garlic, soy sauce",
    height=100,
)

dietary_notes = st.text_input(
    "Any dietary notes? (optional)",
    placeholder="e.g. vegetarian, no dairy, gluten-free",
)

# ---------------------------------------------------------------------------
# UI — additional preferences
# ---------------------------------------------------------------------------
with st.expander("🎛️ More preferences (optional)", expanded=False):
    col1, col2 = st.columns(2)

    with col1:
        age_group = dropdown_or_custom(
            "Who's this for?",
            ["No preference", "Adults", "Kids", "Both / Family"],
            key="age_group",
        )
        protein_pref = dropdown_or_custom(
            "Protein preference",
            ["No preference", "Protein-heavy", "Light / protein-friendly"],
            key="protein_pref",
        )
        cooking_time = dropdown_or_custom(
            "Cooking time",
            ["No preference", "Under 15 min", "15-30 min", "30-60 min", "60+ min"],
            key="cooking_time",
        )
        servings = st.number_input("Servings", min_value=1, max_value=12, value=2)

    with col2:
        spice_level = dropdown_or_custom(
            "Spice level",
            ["No preference", "Mild", "Medium", "Spicy"],
            key="spice_level",
        )
        meal_type = dropdown_or_custom(
            "Meal type",
            ["Any", "Breakfast", "Lunch", "Dinner", "Snack"],
            key="meal_type",
        )
        cuisine = dropdown_or_custom(
            "Cuisine",
            ["No preference", "Indian", "Italian", "Mexican", "Chinese", "Mediterranean", "American"],
            key="cuisine",
        )

# ---------------------------------------------------------------------------
# Generate
# ---------------------------------------------------------------------------
if st.button("🍽️ Get recipe ideas", type="primary"):
    if not ingredients.strip():
        st.error("Please list at least a few ingredients.")
    else:
        preferences = {
            "ingredients": ingredients,
            "Dietary notes": dietary_notes,
            "Who it's for": age_group,
            "Protein preference": protein_pref,
            "Cooking time": cooking_time,
            "Servings": servings,
            "Spice level": spice_level,
            "Meal type": meal_type,
            "Cuisine": cuisine,
        }
        with st.spinner("Cooking up some ideas..."):
            recipes = generate_recipes(preferences)
            st.session_state.recipes = recipes

if "recipes" in st.session_state and st.session_state.recipes:
    for recipe in st.session_state.recipes:
        with st.container(border=True):
            st.subheader(recipe.get("title", "Recipe"))

            uses = recipe.get("uses_ingredients", [])
            if uses:
                st.markdown(f"**Uses:** {', '.join(uses)}")

            extra = recipe.get("extra_ingredients", [])
            if extra:
                st.markdown(f"**You'll also need:** {', '.join(extra)}")

            calories = recipe.get("approx_calories_per_serving")
            if calories:
                st.markdown(f"**Approx. calories/serving:** {calories}")

            st.markdown("**Steps:**")
            for i, step in enumerate(recipe.get("steps", []), 1):
                st.markdown(f"{i}. {step}")
