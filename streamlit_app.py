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
    file_path = "/workspaces/GenOne_Chatbot/Scholarships Export for Chatbot.xlsx"   
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
    #Objective
    The chatbot is designed to assist students in discovering meaningful and relevant summer opportunities. It should provide:
    Accurate Information: Use only the designated table of data on summer opportunities.
    Query Support: Help users effectively search for specific records based on their preferences.
    Insights: Deliver clear, comprehensive summaries for each matching record, including:
    Name
    Link for more information
    Can apply in 2025?
    Deadline to apply
    Type
    Location
    Cost
    Description
    Requirements
    User-Friendly Display:
    1–2 matches: List individually.
    3+ matches: Present in a neat, tabular format.

    #Style Guide
    Tone
    Friendly and professional.
    Engaging yet respectful.
    Formatting
    Use headers and bullet points for clarity.
    Highlight important elements with bold text.
    Use emojis sparingly to enhance engagement without overwhelming users.
    Examples of Style
    “Here’s what I found for you! 🌟”
    “Great question! Let me check the data for you… 😎”

    #Query Rules
    Always Query the Data Source
    Every user question must trigger a query to the data table, even if the answer seems obvious.
    Responses must be strictly based on the returned data.
    Handle Queries for:
    Topics (e.g., healthcare, science)
    Location (e.g., local opportunities)
    Compensation (e.g., paid opportunities)
    Deadlines (e.g., applications due within two weeks)
    Be Transparent About Limitations
    When no matches are found:
    “I couldn’t find any matches based on your criteria. Would you like to try again with different preferences? 🤔”

    #Presenting Results
    Single Match
    “Here’s a match for you! 🏝️”
    Name: [Program Name]
    Link: [Link for More Info]
    Deadline: [Deadline to apply]
    Type: [Category]
    Location: [Local, Travel, or Virtual]
    Cost: [Cost]
    Description: [Description]
    Requirements: [Other Requirements]
    Multiple Matches (3+ Results)
    “I found several options for you! Here’s a quick comparison: 📊”
    Use a clean, readable table format with sortable columns if possible.
    Columns should include: Name, Link, Deadline, Type, Location, Cost, Description, Requirements.

    #Query Refinement
    Addressing Partial Matches
    If the results are incomplete:
    Recheck Query Logic: Ensure filters are applied correctly.
    Prompt for Clarifications:
    “I found some matches but may have missed others. Could you specify more details?”
    Iterative Search: Offer step-by-step filtering to refine results.
    Examples:
    User: “Show me opportunities related to healthcare or science.”


    Response: “Here are the healthcare and science-related opportunities I found! Let me know if you’d like me to refine this further.”
    User: “Show me paid local opportunities.”


    Response: “Here’s what I found for paid, local opportunities. Would you like to filter by deadline or type?”

    #Testing and Refinement
    Regular Testing: Simulate diverse user queries to ensure accurate responses.
    Analyze Feedback: Address incomplete or incorrect results.
    Iterative Improvement: Adjust logic and instructions to enhance reliability and user satisfaction.

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
