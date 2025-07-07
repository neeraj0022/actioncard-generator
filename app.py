import streamlit as st
import pandas as pd
from llm_utils import convert_row_to_json
from form_utils import render_card_form



st.set_page_config(page_title="🤖 Action Card Generator", layout="wide")
st.title("🤖 Action Card Generator", )

uploaded_file = st.file_uploader("📤 Upload Excel (.xls, .xlsx)", type=["xls", "xlsx"])

# Handle file and session state
if uploaded_file:
    if "uploaded_file_data" not in st.session_state:
        df = pd.read_excel(uploaded_file).fillna("")
        st.session_state["uploaded_file_data"] = df
    else:
        df = st.session_state["uploaded_file_data"]

    st.write("🧾 Preview of Excel file:", df.head())

    # Button to convert to JSON
    if st.button("🔄 Convert to JSON Cards") or "cards" in st.session_state:
        if "cards" not in st.session_state:
            cards = []
            for i, row in enumerate(df.to_dict(orient="records")):
                st.write(f"Processing row {i + 1}/{len(df)}…")
                card = convert_row_to_json(row)
                cards.append(card)
            st.session_state["cards"] = cards
            st.success(f"✅ Generated {len(cards)} JSON cards!")

        cards = st.session_state["cards"]
        st.json(cards)

        # Edit first card
        if cards:
            st.markdown("### ✏️ Edit First Card in Form View")
            edited_card = render_card_form(cards[0])


