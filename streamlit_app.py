#import libraries
import streamlit as st
import pandas as pd
import openai
import os

st.title("💬 GenOne Scholarship Opportunity Chatbot")
st.write(
    "This chatbot allows users to query opportunities from a pre-uploaded Excel file. "
    "It uses OpenAI's GPT-4 model to generate responses. To use this app, please provide your OpenAI API key."
)

# Request OpenAI API key
openai_api_key = st.text_input("OpenAI API Key", type="password")
if not openai_api_key:
    st.info("Please add your OpenAI API key to continue.", icon="🗝️")
    st.stop()

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

st.write("### Preview of the Data")
st.write(df.head())

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
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )

        # Debugging:
        st.write("**Debug Response:**", response)

        # Extract and validate the response
        if "choices" in response and len(response["choices"]) > 0:
            # Extract the content from the first choice
            assistant_message = response["choices"][0].get("message", {}).get("content", None)
            if assistant_message:
                st.session_state.messages.append({"role": "assistant", "content": assistant_message})
                with st.chat_message("assistant"):
                    st.markdown(assistant_message)
            else:
                st.error("The assistant generated a response, but it was empty or improperly formatted. Please try again.")
        else:
            st.error("The API returned a response, but it did not contain valid choices. Please try again.")

    except openai.error.OpenAIError as e:
        st.error(f"An OpenAI API error occurred: {e}")
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
