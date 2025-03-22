import streamlit as st
import pandas as pd
import openai
import os
from pyairtable import Table
from pyairtable import Api
from datetime import datetime
import io
import csv


st.set_page_config(layout="wide")

# Airtable credentials
AIRTABLE_PERSONAL_TOKEN = os.getenv("AIRTABLE_PERSONAL_TOKEN")  # Store securely in environment variables
BASE_ID = "appvzxcqpeB4LdvIV"
TABLE_NAME = "Scholarships (LIST)"

# Function to estimate the number of tokens in a string
def num_tokens_from_string(string: str) -> int:
    """Estimate the number of tokens in a string by using a simple heuristic (approx 4 tokens per word)."""
    return len(string.split()) * 4  # Heuristic: Approx 4 tokens per word

# Add a logo at the top of the page
st.image("GenOneLogo.png", width=300)  # Adjust width as needed

st.title("💬Scholarship Opportunity Chatbot")
st.write(
    "This chatbot allows you to query scholarship opportunities compiled by GenOne. "
    "Feel free to fiter by school/demographic (optional)."
    "You can download your results for future reference"
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
@st.cache_data(ttl=60)  # Cache data for only 60 seconds
def load_data():
    if not AIRTABLE_PERSONAL_TOKEN:
        st.error("Missing Airtable personal token. Please contact Admin.")
        st.stop()

    # Authenticate using the personal token
    api = Api(AIRTABLE_PERSONAL_TOKEN)
    table = api.table(BASE_ID, TABLE_NAME)
    # Fetch records
    records = table.all(view="All Scholarships for Chatbot")  # Specify the correct view

    if not records:
        return pd.DataFrame()  # Return empty DataFrame if no data found

   
     # Extract only the fields returned by Airtable (avoiding dynamically adding all possible fields)
    df = pd.DataFrame([record["fields"] for record in records])

    # Ensure "Scholarship Name" is the first column
    if "Scholarship Name" in df.columns:
        cols = ["Scholarship Name"] + [col for col in df.columns if col != "Scholarship Name"]
        df = df[cols]

    # Convert "Deadline this year" to datetime and filter out past deadlines
    if "Deadline this year" in df.columns:
        df["Deadline this year"] = pd.to_datetime(df["Deadline this year"], errors="coerce")

        # Keep records where deadline is either in the future or missing
        today = datetime.today()
        df = df[(df["Deadline this year"].isna()) | (df["Deadline this year"] >= today)]

    # Clean and preprocess data
    df = df.applymap(lambda x: str(x).strip() if isinstance(x, str) else x)
    if "School (if specific)" in df.columns:
     df["School (if specific)"] = df["School (if specific)"].fillna("All (School Unspecified)")
    else:
     df["School (if specific)"] = "All (School Unspecified)"  # Create column with default value if missing


    # Ensure "Demographic" column exists
    if "Demographic focus" not in df.columns:
        df["Demographic focus"] = "Unknown"

    return df

df = load_data()

st.write("### Preview of Scholarships")

# Define the fields to preview
preview_columns = ["Scholarship Name", "Amount", "Minimum GPA", "Deadline this year", "Scholarship Website", "Status of Deadline", "Amount- details", "Renewable?", "Amount Category (per Year)", "Requirements and other Focus:", "Residency Requirements (US, Perm, DACA, All)", "Notes", "Demographic focus", "Region", "School Specific?", "School (if specific)"]

# Ensure only existing columns are used (in case some are missing)
preview_columns = [col for col in preview_columns if col in df.columns]

# Display only the selected columns
st.dataframe(df[preview_columns])


# Extract unique school options from the column
school_options = sorted(df["School (if specific)"].fillna("All (School Unspecified)").unique())  # Fill NaN with "All"
selected_school = st.selectbox(
    "Select the school related to your scholarship search (leave as 'All (No Filter)' for all):",
    ["All (No Filter)"] + school_options  # Add "All (No Filter)" option
)

# Add demographic dropdown only if "All (No Filter)" is not selected
df["Demographic focus"] = df["Demographic focus"].fillna("All (Demography Unspecified)")  # Fill NaN with "All"
demographic_options = sorted(df["Demographic focus"].unique())
selected_demographic = st.selectbox(
    "Select your demographic group (leave as 'All (No Filter)' for all):",
    ["All (No Filter)"] + demographic_options  # Add "All (No Filter)" option
)

# Default to all data if "All (No Filter)" is selected
filtered_data = df.copy()

# Apply filters only if a specific selection is made
if selected_school != "All (No Filter)":
    filtered_data = filtered_data[filtered_data["School (if specific)"] == selected_school]

if selected_demographic != "All (No Filter)":
    filtered_data = filtered_data[filtered_data["Demographic focus"] == selected_demographic]

# Chatbot Logic (stores all previous user messages)
if "messages" not in st.session_state:
    st.session_state.messages = []

# Wait for the user's query
if user_query := st.chat_input("What kind of scholarship opportunities are you looking for?"):
    st.session_state.messages.append({"role": "user", "content": user_query})
    with st.chat_message("user"):
        st.markdown(user_query)

    # Convert filtered data to string for token estimation
    filtered_data_string = filtered_data.to_string(index=False)
    token_count = num_tokens_from_string(filtered_data_string)

    # Prepare the prompt for OpenAI API
    prompt = f"""
    ### Objective
    The chatbot assists users in discovering relevant opportunities by querying the provided data. Responses should include:
    - Relevant details about matching opportunities with all the fields and descriptions
    - A user-friendly display, with tables for multiple matches.
    - ### Table Format Example: | Scholarship Name | Amount | Requirements | Minimum GPA | Scholarship Website | Deadline Status | Deadline this year | School (if specific) | Demographic focus | Notes | 
    - Clarity, friendliness, and professionalism.
    - Make sure to look through the full data and provide all the matching responses.
    - It is important to give ALL matching responses
    - But don't add a respone just for reference only if it does not match all filters of the user query needs.
    - do not have a reponse saying "but were included for completeness", don't include if it doesn't match

    ### Filtered Table Data
    {filtered_data_string}

    ### User Query
    {user_query}
    """
    # Determine which model to use
    model_name = "gpt-4o-mini" if (
        (selected_school == "All (No Filter)" and selected_demographic == "All (No Filter)") or
        (selected_school == "All (School Unspecified)" and selected_demographic == "All (Demography Unspecified)") or
        (selected_school == "All (School Unspecified)" and selected_demographic == "All (No Filter)") or
        (selected_school == "All (No Filter)" and selected_demographic == "All (Demography Unspecified)")
    ) else "gpt-4"


    # Generate Chat Response using OpenAI
    response = client.chat.completions.create(
        model=model_name,
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

    if response_content:
        # Parse response into structured format (assuming response contains a table)
        response_lines = response_content.split("\n")  # Split response by new lines
        structured_data = []

        for line in response_lines:
            fields = [field.strip() for field in line.split("|")]  # Split by '|' and clean whitespace
            if len(fields) > 1:  # Ensure it's not an empty line or header
                structured_data.append(fields)

        # Convert structured data to DataFrame
        if structured_data:
            # Extract headers and data
            headers = structured_data[0]  # Assuming first row contains headers
            rows = structured_data[1:]  # The rest are actual data

            # Create DataFrame
            response_df = pd.DataFrame(rows, columns=headers)

            # Convert DataFrame to CSV format
            csv_buffer = io.StringIO()
            response_df.to_csv(csv_buffer, index=False)

            # Convert to downloadable file
            st.download_button(
                label="📥 Download Chatbot Response as CSV",
                data=csv_buffer.getvalue().encode("utf-8"),
                file_name="chatbot_response.csv",
                mime="text/csv",
            )
