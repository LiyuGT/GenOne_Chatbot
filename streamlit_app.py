import streamlit as st
import pandas as pd
import openai

# Title and description
st.title("💬 Opportunity Chatbot")
st.write(
    "This chatbot allows users to query opportunities from a pre-uploaded Excel file. "
    "It uses OpenAI's GPT-4 model to generate responses. To use this app, please provide your OpenAI API key."
)

# Step 1: Request OpenAI API key
openai_api_key = st.text_input("OpenAI API Key", type="password")
if not openai_api_key:
    st.info("Please add your OpenAI API key to continue.", icon="🗝️")
    st.stop()

# Step 2: Load the Excel file from the repository
@st.cache_data
def load_data():
    file_path = "./workspaces/GenOne_Chatbot/Scholarships Export for Chatbot.xlsx"  
    return pd.read_excel(file_path)

df = load_data()

st.write("### Preview of the Data")
st.write(df.head())

# Step 3: Initialize OpenAI API
openai.api_key = openai_api_key

# Step 4: Chatbot Logic
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Step 5: User Input
if user_query := st.chat_input("What opportunities are you looking for?"):

    # Add the user query to the session state
    st.session_state.messages.append({"role": "user", "content": user_query})
    with st.chat_message("user"):
        st.markdown(user_query)

    # Create a GPT-4 prompt with the data and user query
    prompt = f"""
    The following table contains data about summer opportunities:

    {df.head(3).to_string(index=False)}

    Columns available: {', '.join(df.columns)}.

    User Query: {user_query}

    Write Python code to filter the DataFrame (df) to provide the user with relevant information 
    based on their query. The result should be a string or tabular response to display back to the user.
    """

    # Call OpenAI API to generate Python code
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that generates Python code to query DataFrames."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=300,
        temperature=0,
    )

    # Extract and execute the Python code from the response
    code = response['choices'][0]['message']['content']
    with st.chat_message("assistant"):
        st.markdown("Let me process that for you...")

    try:
        local_vars = {}
        exec(code, {"df": df}, local_vars)
        result = local_vars.get("result", "No result variable returned.")

        # Display the result
        st.session_state.messages.append({"role": "assistant", "content": str(result)})
        with st.chat_message("assistant"):
            st.markdown(str(result))

    except Exception as e:
        error_message = f"Error executing the generated code: {str(e)}"
        st.session_state.messages.append({"role": "assistant", "content": error_message})
        with st.chat_message("assistant"):
            st.markdown(error_message)
