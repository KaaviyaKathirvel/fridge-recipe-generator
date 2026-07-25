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
# Recipe generation
# ---------------------------------------------------------------------------
def generate_recipes(ingredients: str, dietary_notes: str = "") -> list:
    """
    Ask the LLM for 2-3 recipe ideas using the given ingredients.
    Returns a list of dicts with title, uses_ingredients, extra_ingredients,
    and steps.
    """
    system_instructions = (
        "You are a helpful, creative home cooking assistant. "
        "You always respond with a single valid JSON object and nothing else - "
        "no markdown fences, no commentary."
    )

    dietary_line = f"\nDietary notes to respect: {dietary_notes}" if dietary_notes.strip() else ""

    prompt = f"""
The user has these ingredients on hand: {ingredients}{dietary_line}

Suggest 2-3 simple, realistic recipes they could make, prioritizing dishes that use
mostly what they already have. It's fine to assume basic pantry staples (salt, pepper,
oil, water) are available even if not listed.

Return ONLY a JSON object with this exact shape:
{{
  "recipes": [
    {{
      "title": "Recipe name",
      "uses_ingredients": ["ingredient1", "ingredient2"],
      "extra_ingredients": ["anything needed that they didn't list, besides basic staples"],
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
# UI
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

if st.button("🍽️ Get recipe ideas", type="primary"):
    if not ingredients.strip():
        st.error("Please list at least a few ingredients.")
    else:
        with st.spinner("Cooking up some ideas..."):
            recipes = generate_recipes(ingredients, dietary_notes)
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

            st.markdown("**Steps:**")
            for i, step in enumerate(recipe.get("steps", []), 1):
                st.markdown(f"{i}. {step}")
