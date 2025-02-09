import streamlit as st
import pandas as pd
import openai
import os
from pyairtable import Table
from pyairtable import Api

# Airtable credentials
AIRTABLE_PERSONAL_TOKEN = os.getenv("AIRTABLE_PERSONAL_TOKEN")  # Store securely in environment variables
BASE_ID = "appT6A7hwVgEpbGPR"
TABLE_NAME = "Scholarships (LIST)-All Scholarship by due date"

# Function to estimate the number of tokens in a string
def num_tokens_from_string(string: str) -> int:
    """Estimate the number of tokens in a string by using a simple heuristic (approx 4 tokens per word)."""
    return len(string.split()) * 4  # Heuristic: Approx 4 tokens per word

# Add a logo at the top of the page
st.image("GenOneLogo.png", width=300)  # Adjust width as needed

st.title("💬Scholarship Opportunity Chatbot")
st.write(
    "This chatbot allows users to query opportunities from Airtable. "
    "It uses OpenAI's GPT-4 model to generate responses."
)

# Load the OpenAI API key securely from environment variables
openai_api_key = os.getenv("OPENAI_API_KEY")

if not openai_api_key:
    st.error("Please contact Admin for issue associated with missing OpenAI API key.")
else:
    openai.api_key = openai_api_key  # Set OpenAI API key

# OpenAI API client using the provided API key
client = openai.Client(api_key=openai_api_key)

# Load data from Airtable
@st.cache_data
def load_data():
    if not AIRTABLE_PERSONAL_TOKEN:
        st.error("Missing Airtable personal token. Please contact Admin.")
        st.stop()

    # Authenticate using the personal token
    api = Api(AIRTABLE_PERSONAL_TOKEN)
    table = api.table(BASE_ID, TABLE_NAME)
    # Fetch records
    records = table.all()

    if not records:
        return pd.DataFrame()  # Return empty DataFrame if no data found

    # Collect all possible columns dynamically
    all_columns = set()
    for record in records:
        all_columns.update(record["fields"].keys())

    # Convert Airtable records to DataFrame, ensuring all columns are included
    df = pd.DataFrame([{col: record["fields"].get(col, None) for col in all_columns} for record in records])

    # Ensure "Scholarship Name" is the first column
    if "Scholarship Name" in df.columns:
        cols = ["Scholarship Name"] + [col for col in df.columns if col != "Scholarship Name"]
        df = df[cols]

    # Clean and preprocess data
    df = df.applymap(lambda x: str(x).strip() if isinstance(x, str) else x)
    df["School (if specific)"] = df["School (if specific)"].fillna("All")

    # Ensure "Demographic" column exists
    if "Demographic focus" not in df.columns:
        df["Demographic focus"] = "Unknown"

    return df

df = load_data()
st.write("### Preview of all Scholarships")
st.dataframe(df)

# Extract unique school options from the column
school_options = sorted(df["School (if specific)"].unique())

# Dropdown for school selection
selected_school = st.selectbox("Select the school related to your scholarship search:", school_options)

# Add demographic dropdown only if "All" is selected
if selected_school == "All":
    df["Demographic focus"] = df["Demographic focus"].fillna("All")
    demographic_options = sorted(df["Demographic focus"].unique())
    selected_demographic = st.selectbox("Select your demographic group:", demographic_options)
else:
    selected_demographic = None

# Chatbot Logic (stores all previous user messages)
if "messages" not in st.session_state:
    st.session_state.messages = []

# Wait for the user's query
if user_query := st.chat_input("What kind of scholarship opportunities are you looking for?"):
    st.session_state.messages.append({"role": "user", "content": user_query})
    with st.chat_message("user"):
        st.markdown(user_query)

    # Filter data based on selected school
    if selected_school == "All":
        filtered_data = df[df["School (if specific)"] == "All"]
        if selected_demographic and selected_demographic != "All":
            filtered_data = filtered_data[filtered_data["Demographic focus"] == selected_demographic]
    else:
        filtered_data = df[df["School (if specific)"] == selected_school]

    # Convert filtered data to string for token estimation
    filtered_data_string = filtered_data.to_string(index=False)
    token_count = num_tokens_from_string(filtered_data_string)

    # If tokens exceed 10,000, limit to 20 rows
    if token_count > 10000:
        filtered_data = filtered_data.head(15)

    # Convert final filtered data to string for OpenAI
    filtered_data_string = filtered_data.to_string(index=False)

    # Prepare the prompt for OpenAI API
    prompt = f"""
    ### Objective
    The chatbot assists users in discovering relevant opportunities by querying the provided data. Responses should include:
    - Relevant details about matching opportunities, including name, website, deadline, requirements, etc.
    - A user-friendly display, with tables for multiple matches.
    - ### Table Format Example: | Scholarship Name | Amount | Requirements | Minimum GPA | Scholarship Website | Deadline Status | School (if specific) | Demographic focus | Notes | 
    - Clarity, friendliness, and professionalism.
    - Make sure to look through the full data and provide all the matching responses.

    ### Filtered Table Data
    {filtered_data_string}

    ### User Query
    {user_query}
    """

    # Generate Chat Response using OpenAI
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful student assistant."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )

    response_content = response.choices[0].message.content if response and hasattr(response, "choices") else ""

    if response_content:
        st.write("### Matching Scholarship Opportunities")
        st.write(response_content)

    # Feature to download filtered results as CSV
    if not filtered_data.empty:
        csv = filtered_data.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download Results as CSV",
            data=csv,
            file_name="filtered_scholarships.csv",
            mime="text/csv",
        )
