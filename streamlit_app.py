#import libraries
import streamlit as st
import pandas as pd
import openai
import os
import io

st.title("💬 GenOne Scholarship Opportunity Chatbot")
st.write(
    "This chatbot allows users to query opportunities from a pre-uploaded Excel file. "
    "It uses OpenAI's GPT-4 model to generate responses. "
)

# Load the OpenAI API key securely from environment variables
openai_api_key = os.getenv("OPENAI_API_KEY")

if not openai_api_key:
    st.error("Please contact Admin for issue associated with missing OpenAI API key.")
else:
    openai.api_key = openai_api_key  # Set OpenAI API key



client = openai.Client(api_key=openai_api_key)

# Load the Excel file
@st.cache_data
def load_data():
    file_path = "Scholarships Export for Chatbot.xlsx"  # File uploaded in the same directory
    if not os.path.exists(file_path):
        st.error(f"File not found: {file_path}")
        st.stop()
    
    # Read the file
    df = pd.read_excel(file_path)
    df = df.applymap(lambda x: str(x).strip() if isinstance(x, str) else x)
    
    # Replace empty cells in the "School (if specific)" column with "none"
    df["School (if specific)"] = df["School (if specific)"].fillna("none")
    return df

df = load_data()

st.write("### Preview of all Scholarships")
st.dataframe(df)

# Extract unique school options from the column
school_options = sorted(df["School (if specific)"].unique())

# Dropdown for school selection
selected_school = st.selectbox("Select the school related to your scholarship search:", school_options)

# Chatbot Logic
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Wait for the user's query
if user_query := st.chat_input("What kind of scholarship opportunities are you looking for?"):

    # Add the user query to the session state
    st.session_state.messages.append({"role": "user", "content": user_query})
    with st.chat_message("user"):
        st.markdown(user_query)

    # Filter data based on selected school
    filtered_data = df if selected_school == "none" else df[df["School (if specific)"] == selected_school]

    # Prepare the prompt for OpenAI API
    prompt = f"""
    ### Objective
    The chatbot assists users in discovering relevant opportunities by querying the provided data. Responses should include:
    - Relevant details about matching opportunities, including name, website, deadline, requirements, etc.
    - A user-friendly display, with tables for multiple matches.
    - Clarity, friendliness, and professionalism.
    - Make sure to look through the full data and provide all the matching responses.

    ### Filtered Table Data
    {filtered_data.to_string(index=False)}

    ### User Query
    {user_query}
    """

    # Generate Chat Response using the OpenAI client

    response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": prompt},
    ],
    temperature=0.2,
)

# Extract the actual response content safely
if response and response.choices:
    response_content = response.choices[0].message.content
else:
    response_content = "No response received from OpenAI."

# Function to parse OpenAI response into structured format
def parse_scholarships(response_content):
    lines = response_content.split("\n")
    scholarships = []

    # Identify table lines and process them
    for line in lines:
        parts = line.split("|")
        if len(parts) >= 5:
            scholarships.append([p.strip() for p in parts[1:-1]])  # Remove empty parts

    # Convert parsed data into DataFrame
    if scholarships:
        df_scholarships = pd.DataFrame(scholarships[1:], columns=scholarships[0])  # First row as headers
        return df_scholarships
    else:
        return pd.DataFrame()  # Return empty if no data found

# Debug: Show raw response from OpenAI
st.write("### OpenAI Response Debug")
st.write("##### Response should be in the Choices row, double-click to see")
st.text(response_content)  # Display raw text response for debugging

# Parse response into a structured table
df_scholarships = parse_scholarships(response_content)

# Display the scholarships table in the required format
if not df_scholarships.empty:
    df_scholarships = df_scholarships[["Scholarship Name", "Amount", "Requirements", "Scholarship Website", "Deadline Status"]]
    st.write("### Matching Scholarship Opportunities")
    st.dataframe(df_scholarships)
else:
    st.write("No scholarships found matching your query.")
