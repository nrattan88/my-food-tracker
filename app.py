import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import altair as alt

# --- CONFIGURATION ---
st.set_page_config(page_title="HB Food Tracker", page_icon="🥗")

# --- DATA: FOOD LISTS FROM PDF ---
# Extracted from Harvey Brooker Daily Food Record and Planner
FOOD_DB = {
    "Protein": [
        "Cooked Protein (1 oz)", "Cottage Cheese (2 oz)", "Egg (1 medium)", "Egg Whites (2 tbsp)",
        "Hard Cheese (1 oz)", "Shellfish (Clams, Crab, Lobster)", "Chicken Breast", "Turkey Breast",
        "Legumes (1/2 cup)", "Tofu (1 oz)", "Peanut Butter (1 tbsp)", "Fish (White fish/Salmon)"
    ],
    "Grain/Starch": [
        "Bread (1 oz)", "Melba Toast (4 rect/6 round)", "English Muffin (1/2)", "Whole Wheat Pita (1/2)",
        "Bagel (1/2)", "Rice (1/3 cup cooked)", "Potato (1 small baked)", "Pasta (1/2 cup cooked)",
        "Cereal (1/2 cup)", "Corn (1/2 cup)"
    ],
    "Fruit": [
        "Apple (1 medium)", "Banana (1 small)", "Blueberries (1/2 cup)", "Grapes (1/2 cup)",
        "Orange (1 medium)", "Peach (1 medium)", "Pear (1 small)", "Strawberries (1 cup)"
    ],
    "Milk": [
        "Skim Milk (8 oz)", "Low Fat Yogurt (3/4 cup)", "Almond Milk (1 cup)", "2% Milk (1/2 cup)"
    ],
    "Fat": [
        "Margarine/Butter (1 tsp)", "Oil (1 tsp)", "Mayonnaise (1 tsp)", "Salad Dressing (2 tsp)",
        "Avocado (1/4 medium)"
    ],
    "Dinner Veg": [
        "Asparagus", "Broccoli", "Carrots", "Green Beans", "Spinach", "Tomato", "Mixed Veg (1/2 cup)"
    ],
    "Sanity Savers / Free": [
        "Popcorn (2 cups plain)", "Pretzels (1 oz)", "Ketchup (2 tsp)", "Salsa", "Diet Jello",
        "Clear Soup", "Coffee/Tea"
    ]
}

# --- TARGETS BASED ON PDF [cite: 298, 361, 440, 516, 539, 503] ---
BASE_TARGETS = {
    "Protein": 9.0,
    "Grain/Starch": 5.0,
    "Fruit": 3.0,
    "Milk": 1.0,
    "Fat": 1.0,
    "Dinner Veg": 1.0
}

# --- APP HEADER ---
st.title("HB Daily Tracker")

# --- LEVEL SELECTION  ---
# Allows toggling between Basic, Level 1, 2, and 3
level = st.selectbox("Select Program Level", ["Basic Plan", "Level 1 (+2 units)", "Level 2 (+4 units)", "Level 3 (+6 units)"])

# Determine allowance message
if level == "Basic Plan":
    extra_allowance = 0
    st.info("Goal: Hit the base targets.")
elif level == "Level 1 (+2 units)":
    extra_allowance = 2
    st.info("Level 1: You have **2 extra units** to use on Protein, Fruit, Milk, or Veg.")
elif level == "Level 2 (+4 units)":
    extra_allowance = 4
    st.info("Level 2: You have **4 extra units**. Max 2 can be Grains/Sanity Savers.")
else:
    extra_allowance = 6
    st.info("Level 3: You have **6 extra units**.")

# --- CONNECT TO GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)
try:
    existing_data = conn.read(worksheet="Sheet1", usecols=list(range(6)), ttl=5)
    existing_data = existing_data.dropna(how="all")
except:
    st.error("Could not connect to Google Sheet. Please check your secrets setup.")
    existing_data = pd.DataFrame(columns=["Date", "Meal", "Category", "Food", "Units", "Notes"])

# --- INPUT FORM ---
st.subheader("Log Food")
with st.form("entry_form"):
    date_entry = st.date_input("Date", datetime.today())
    col1, col2 = st.columns(2)
    with col1:
        meal = st.selectbox("Meal", ["Breakfast", "Lunch", "Dinner", "Snack"])
        category = st.selectbox("Category", list(FOOD_DB.keys()) + ["Other"])
    
    with col2:
        # Dynamic dropdown: If category is chosen, show relevant foods
        if category in FOOD_DB:
            food_item = st.selectbox("Food Item", FOOD_DB[category] + ["Custom Entry"])
        else:
            food_item = "Custom Entry"
        
        # If 'Custom Entry' or 'Other' is selected, show a text box
        if food_item == "Custom Entry" or category == "Other":
            custom_food = st.text_input("Type Food Name")
            final_food_name = custom_food
        else:
            final_food_name = food_item

    units = st.number_input("Units", min_value=0.5, step=0.5, value=1.0)
    notes = st.text_input("Notes (optional)")
    
    submitted = st.form_submit_button("Add Log")

    if submitted:
        # Create a new row of data
        new_entry = pd.DataFrame([
            {
                "Date": date_entry.strftime("%Y-%m-%d"),
                "Meal": meal,
                "Category": category,
                "Food": final_food_name,
                "Units": units,
                "Notes": notes
            }
        ])
        # Append to existing data and update Google Sheet
        updated_df = pd.concat([existing_data, new_entry], ignore_index=True)
        conn.update(worksheet="Sheet1", data=updated_df)
        st.success("Food added!")
        st.rerun()

# --- DASHBOARD & ANALYSIS ---
st.divider()
st.subheader("Daily Progress")

# Filter data for the selected date
mask = existing_data["Date"] == date_entry.strftime("%Y-%m-%d")
today_data = existing_data[mask]

if not today_data.empty:
    # Calculate totals by category
    totals = today_data.groupby("Category")["Units"].sum()
    
    # Display progress bars for Core Categories
    cols = st.columns(2)
    idx = 0
    total_core_units = 0
    
    for cat, limit in BASE_TARGETS.items():
        consumed = totals.get(cat, 0)
        total_core_units += consumed
        
        # Calculate percentage for progress bar (capped at 1.0 for visual)
        progress = min(consumed / limit, 1.0)
        
        # Display in columns
        with cols[idx % 2]:
            st.metric(f"{cat}", f"{consumed} / {limit}", delta=float(limit-consumed), delta_color="inverse")
            st.progress(progress)
        idx += 1
    
    # Summary of Total Units vs Level Allowance
    st.write("---")
    total_today = today_data["Units"].sum()
    base_total = sum(BASE_TARGETS.values())
    st.caption(f"**Total Units Today:** {total_today}")
    
    if total_today > base_total:
        overage = total_today - base_total
        if overage <= extra_allowance:
            st.success(f"You are {overage} units over base, which fits within your Level Allowance ({extra_allowance}).")
        else:
            st.warning(f"You are {overage} units over base. (Level Allowance is {extra_allowance}).")
            
else:
    st.info("No food logged for this date yet.")

# --- HISTORY TAB ---
with st.expander("View Full History"):
    st.dataframe(existing_data)
    
    # Simple Chart: Units over time
    if not existing_data.empty:
        chart_data = existing_data.groupby("Date")["Units"].sum().reset_index()
        chart = alt.Chart(chart_data).mark_bar().encode(
            x='Date',
            y='Units',
            tooltip=['Date', 'Units']
        ).interactive()
        st.altair_chart(chart, use_container_width=True)
