import streamlit as st
from llm_utils import convert_row_to_json

# Define schema for dynamic rule builder
FIELD_SCHEMA = {
    "upgradeEligibility.eligibilityStatus": {"type": "enum", "options": ["Y", "N", "U"]},
    "contract_end_date": {"type": "number", "qualifiers": ["days_until"]},
    "contract_start_date": {"type": "number", "qualifiers": ["days_since"]},
    "device_android": {"type": "boolean"},
    "device_google": {"type": "boolean"},
    "flex_pay_eligible": {"type": "enum", "options": ["Y", "N"]},
    "ee_service_mrc_incl_vat": {"type": "number"},
    "ee_high_credit_risk_score": {"type": "boolean"},
    # Add more fields as needed
}

OPERATORS = ["=", "!=", "<", ">", "<=", ">="]


def render_rules(rules, path=""):
    """
    Recursively render a list of rules or groups.
    Returns the updated rules list.
    """
    new_rules = []
    for idx, rule in enumerate(rules):
        key_base = f"{path}_{idx}"
        if rule.get("type") == "group":
            with st.expander(f"{rule.get('conjunction', 'AND')} Group {idx+1}", expanded=True):
                conj = st.selectbox(
                    "Conjunction",
                    ["AND", "OR"],
                    index=["AND", "OR"].index(rule.get("conjunction", "AND")),
                    key=f"{key_base}_conj"
                )
                updated = render_rules(rule.get("rules", []), path=key_base)
                new_rules.append({
                    "type": "group",
                    "conjunction": conj,
                    "rules": updated
                })
        else:
            col1, col2, col3, col4 = st.columns([3, 2, 3, 3])
            with col1:
                field = st.selectbox(
                    "Field",
                    list(FIELD_SCHEMA.keys()),
                    index=list(FIELD_SCHEMA.keys()).index(rule.get("field", list(FIELD_SCHEMA.keys())[0])),
                    key=f"{key_base}_field"
                )
            meta = FIELD_SCHEMA[field]

            with col2:
                qualifier = None
                if meta.get("qualifiers"):
                    qualifier = st.selectbox(
                        "Qualifier",
                        meta["qualifiers"],
                        index=meta["qualifiers"].index(rule.get("qualifier", meta["qualifiers"][0])),
                        key=f"{key_base}_qual"
                    )
                else:
                    st.markdown("—", unsafe_allow_html=True)

            with col3:
                operator = st.selectbox(
                    "Operator",
                    OPERATORS,
                    index=OPERATORS.index(rule.get("operator", "=")),
                    key=f"{key_base}_op"
                )

            with col4:
                if meta["type"] == "boolean":
                    value = st.selectbox(
                        "Value",
                        ["true", "false"],
                        index=["true", "false"].index(str(rule.get("value", "false"))),
                        key=f"{key_base}_val"
                    )
                elif meta["type"] == "enum":
                    value = st.selectbox(
                        "Value",
                        meta["options"],
                        index=meta["options"].index(rule.get("value", meta["options"][0])),
                        key=f"{key_base}_val"
                    )
                else:
                    value = st.text_input(
                        "Value",
                        value=str(rule.get("value", "")),
                        key=f"{key_base}_val"
                    )

            new_rule = {
                "type": "rule",
                "field": field,
                "operator": operator,
                "value": value
            }
            if qualifier:
                new_rule["qualifier"] = qualifier
            new_rules.append(new_rule)

    # Buttons to add rule or group at this level
    col_add, col_group = st.columns(2)
    with col_add:
        if st.button("➕ Add Rule", key=f"{path}_add_rule"):
            new_rules.append({
                "type": "rule",
                "field": list(FIELD_SCHEMA.keys())[0],
                "operator": "=",
                "value": ""
            })
    with col_group:
        if st.button("➕ Add Group", key=f"{path}_add_group"):
            new_rules.append({
                "type": "group",
                "conjunction": "AND",
                "rules": []
            })

    return new_rules



def render_card_form(card: dict) -> dict:
    st.markdown("## 📝 Card Form Editor")

    # Prevent key errors on rerun
    card.setdefault("sections", {})
    card.setdefault("metadata", {})
    card.setdefault("tags", {})
    card.setdefault("eligibilityRules", None)
    card.setdefault("contentVariants", [{}])

    # Tabs
    tab1, tab2, tab3 = st.tabs(["🎯 Action Details", "📜 Business Rules", "📱 Content Variants"])

    # --- Tab 1: Action Details ---
    with tab1:
        st.subheader("Basic Info")
        card["name"] = st.text_input("Name (User-friendly Action Name)", value=card.get("name", ""))
        card["actionCardId"] = st.text_input("Template ID (actionCardId)", value=card.get("actionCardId", ""))
        card["description"] = st.text_area("Description", value=card.get("description", ""))
        card["enabled"] = st.checkbox("Enabled (Visible to customers)", value=card.get("enabled", True))



        st.subheader("Metadata")
        metadata = card["metadata"]

        metadata["manufacturer"] = st.text_input("Manufacturer", value=metadata.get("manufacturer", ""))
        metadata["location"] = st.text_input("Location", value=metadata.get("location", ""))
        metadata["productType"] = st.text_input("Product Type", value=metadata.get("productType", ""))
        metadata["activeState"] = st.text_input("Active State", value=metadata.get("activeState", ""))

        # Define allowed options
        all_channels = ["App", "Web", "Store", "IVR"]
        current_channels = metadata.get("channel", [])

        # Validate and filter default values
        valid_channels = [ch for ch in current_channels if ch in all_channels]
        invalid_channels = [ch for ch in current_channels if ch not in all_channels]

        # Display multiselect
        metadata["channel"] = st.multiselect(
            "Channels",
            options=all_channels,
            default=valid_channels,
        )

        # Optional warning for any invalid/default values
        if invalid_channels:
            st.warning(f"Ignored invalid channels: {', '.join(invalid_channels)}")

        # Update card metadata
        card["metadata"] = metadata


        st.subheader("Tags")
        tags = card.setdefault("tags", {})
        allowed_product = ["Broadband Base Package", "TV AddOn", "Sport Base Package", "Handset", "Flex Pay", "Samsung", "Android", "Apple"]
        allowed_life = ["XSell", "Acquisition", "ERCW", "Upgrade", "Existing Customer"]
        allowed_intent = ["Sell", "Inform", "Prompt", "Purchase", "Upgrtade", "Pre-order", "Order"]
        allowed_business = ["U&R Home", "XSELL PAYM - Deepsell", "Benefit Reinforcement", "Proactive Service", "Upgrade", "Flex Pay"," New Device", "Flagship" ]

        # Filter defaults
        default_product = [t for t in tags.get("Product Tags", []) if t in allowed_product]
        default_life = [t for t in tags.get("Life Stage Tags", []) if t in allowed_life]
        default_intent = [t for t in tags.get("Intent Tags", []) if t in allowed_intent]
        default_business = [t for t in tags.get("Business Label Tags", []) if t in allowed_business]

        card["productTags"] = st.multiselect("Product Tags", allowed_product, default=default_product)
        card["lifestageTags"] = st.multiselect("Lifestage Tags", allowed_life, default=default_life)
        card["intentTags"] = st.multiselect("Intent Tags", allowed_intent, default=default_intent)
        card["businessLabelTags"] = st.multiselect("Business Label Tags", allowed_business, default=default_business)

        card["tags"] = {
            "Product Tags": card["productTags"],
            "Life Stage Tags": card["lifestageTags"],
            "Intent Tags": card["intentTags"],
            "Business Label Tags": card["businessLabelTags"],
        }
        
        st.subheader("Sections")
        sections = card["sections"]
        sections["location"] = st.text_input("Section Location", value=sections.get("location", ""))
        sections["channel"] = st.multiselect("Section Channel", ["App", "Web", "Store", "IVR"], default=sections.get("channel", ["App", "Web"]))
        card["sections"] = sections



    # --- Tab 2: Business Rules ---
    with tab2:
        st.subheader("Eligibility Rules")

        rules = card.get("eligibilityRules")
        if rules is None:
            rules = [{"type": "group", "conjunction": "AND", "rules": []}]

        updated_rules = render_rules(rules, path="root")
        card["eligibilityRules"] = updated_rules

        st.json(updated_rules)
        
    with tab3:
        st.subheader("Content Variants")
        content = card["contentVariants"][0]
        content["deviceFeature"] = st.text_input("Device Feature", value=content.get("deviceFeature", ""))
        content["body"] = st.text_area("Body", value=content.get("body", ""))
        content["title"] = st.text_input("Title", value=content.get("title", ""))
        content["ctaText"] = st.text_input("CTA Text", value=content.get("ctaText", ""))
        content["appDeepLink"] = st.text_input("App Deep Link", value=content.get("appDeepLink", ""))
        content["webUrl"]= st.text_input("Web URL", value=content.get("webUrl", ""))
        card["contentVariants"] = [content]
        

    return card

