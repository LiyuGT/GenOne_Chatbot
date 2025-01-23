import streamlit as st
import pandas as pd
import openai
import os

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

# Step 2: Load the Excel file and preprocess it
@st.cache_data
def load_and_preprocess_data():
    file_path = "Scholarships Export for Chatbot.xlsx"  # File in the same directory
    if not os.path.exists(file_path):
        st.error(f"File not found: {file_path}")
        st.stop()
    
    # Load the data
    df = pd.read_excel(file_path)
    
    # Ensure Arrow compatibility by converting columns
    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = df[col].astype(str)  # Convert object columns to string
    
    # Clean "Amount Details" column
    if "Amount Details" in df.columns:
        df["Amount Details"] = df["Amount Details"].fillna("").astype(str)  # Ensure non-null strings
    
    return df

df = load_and_preprocess_data()

# Display a preview of the data
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
    
    ## **Objective**
    The chatbot assists students in discovering relevant summer opportunities by providing:  
    - **Accurate Information**: Answers must be based **exclusively** on the designated table of scholarships. No external sources are used.  
    - **Query Support**: Helps users search for scholarships based on specific criteria.  
    - **Comprehensive Insights**: Delivers clear summaries for each matching scholarship, including:  
    - Scholarship Name  
    - Scholarship Website  
    - Status of Deadline  
    - Deadline This Year  
    - Resource Type  
    - Amount (Details)  
    - Requirements and Other Focus  
    - Demographic Focus  
    - Notes  

    - **User-Friendly Display**:  
    - **1–2 matches**: Present individually.  
    - **3+ matches**: Use a structured table format.  

    ---

    ## **Style Guide**
    ### **Tone**  
    - Friendly and professional.  
    - Engaging yet respectful.  

    ### **Formatting**  
    - Use **headers** and **bullet points** for clarity.  
    - Highlight key details with **bold text**.  
    - Use emojis sparingly to enhance engagement without overwhelming users.  

    ### **Examples of Style**  
    - "Here’s what I found for you! 🌟"  
    - "Great question! Let me check the data for you… 😎"  

    ---

    ## **Query Rules**
    ### **General Guidelines**  
    1. **Always query the data source** for every user question.  
    2. **Base responses strictly on returned data**.  
    3. Always return all results that match the query criteria

    ### **Specific Query Types**  
    - **Demographic Focus**: E.g., scholarships for specific racial/ethnic groups.  Any questions related to race, ethnicity, minorities should use the field called "Demographic Focus" to determine matches.
    - **Region**: E.g., local, state-level (e.g., North Carolina), or national scholarships.  
    - **Amount**: Use data from the "amount details" or "amount category" field.  
    - **Deadlines**: Use the "deadline this year" field. If empty, inform users:  
    - "We don’t have this year’s deadline yet, but last year it was [Deadline Last Year]."  

    ### **Transparent Handling of Limitations**  
    - **No Matches Found**:  
    - "I couldn’t find any matches based on your criteria. Would you like to try again with different preferences? 🤔"  

    ---

    ## **Presenting Results**
    ### **1–2 Matches**  
    - "Here’s a match for you! 🏝️"  
    - **Name**: [Scholarship Name]  
    - **Website**: [Scholarship Website]  
    - **Deadline This Year**: [Deadline This Year]  
    - **Status of Deadline**: [Status of Deadline]  
    - **Region**: [Region]  
    - **Requirements**: [Requirements and Other Focus]  
    - **Amount**: [Amount Details]  
    - **Demographic Focus**: [Demographic Focus]  
    - **Notes**: [Notes]  

    ### **3+ Matches**  
    - "I found several options for you! Here’s a quick comparison: 📊"  
    - Use a clean, readable table format with sortable columns if possible. Include these fields:  
    - Scholarship Name  
    - Scholarship Website  
    - Status of Deadline  
    - Deadline This Year  
    - Resource Type  
    - Amount  
    - Requirements and Other Focus  
    - Demographic Focus  
    - Notes  

    ---

    ## **Query Refinement**
    ### **Handling Partial Matches**  
    1. **Recheck Query Logic**: Ensure filters are applied correctly.  
    2. **Prompt for Clarifications**:  
    - "I found some matches but may have missed others. Could you specify more details?"  
    3. **Offer Iterative Search**: Suggest step-by-step refinements.  

    ### **Example Scenarios**  
    **User**: "Show me scholarships for African Americans."  
    - **Response**: "Here are scholarships with a demographic focus of African Americans! Let me know if you’d like me to refine this further."  

    **User**: "Show me local scholarships only."  
    - **Response**: "Here’s what I found for local scholarships. Would you like to filter by deadline or type?"  

    ---

    ## **Testing and Refinement**
    1. **Regular Testing**: Simulate diverse user queries to ensure the chatbot handles edge cases.  
    2. **Analyze Feedback**: Address incomplete, incorrect, or unclear results promptly.  
    3. **Iterative Improvement**: Continuously adjust logic and instructions to improve reliability and user satisfaction.


    # Testing and Refinement
    Regular Testing: Simulate diverse user queries to ensure accurate responses.
    Analyze Feedback: Address incomplete or incorrect results.
    Iterative Improvement: Adjust logic and instructions to enhance reliability and user satisfaction.

    """
    
    # Generate Chat Response using OpenAI API
    # Generate Chat Response using the new synchronous OpenAI API method
    response = openai.chat.completions.create( 
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ],
    )

    if "choices" in response and len(response["choices"]) > 0:
        result = response["choices"][0].get("message", {}).get("content", None)
        if result:
            st.session_state.messages.append({"role": "assistant", "content": result})
            with st.chat_message("assistant"):
                st.markdown(result)
        else:
            st.error("The response is empty. Please try again or adjust your query.")