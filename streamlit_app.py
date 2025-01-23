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

# Step 2: Initialize OpenAI client
client = openai.Client(api_key=openai_api_key)

# Step 3: Load the Excel file from the repository
@st.cache_data
def load_data():
    file_path = "Scholarships Export for Chatbot.xlsx"  # File in the same directory
    if not os.path.exists(file_path):
        st.error(f"File not found: {file_path}")
        st.stop()
    # Ensure data is converted to compatible types to avoid errors
    df = pd.read_excel(file_path)
    df = df.applymap(lambda x: str(x).strip() if isinstance(x, str) else x)
    return df

df = load_data()

st.write("### Preview of the Data")
st.write(df.head())

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

    # Step 6: Filter the Data Based on User's Query
    # For this example, let's filter based on 'Demographic Focus' or 'Scholarship Name' fields
    matched_df = df[df.apply(lambda row: row.astype(str).str.contains(user_query, case=False).any(), axis=1)]
    
    if matched_df.empty:
        st.error("No scholarships found matching your query. Please try again with different criteria.")
    else:
        # Step 7: Prepare the prompt for GPT
        prompt = f"""
        ### Objective
        The chatbot assists users in discovering relevant opportunities by querying the provided data. Responses should include:
        - Relevant details about matching opportunities, including name, website, deadline, requirements, etc.
        - A user-friendly display, with tables for multiple matches.
        - Clarity, friendliness, and professionalism.

        User Query: {user_query}
        Data Source: Use the table provided for matching opportunities.

        ### Matching Scholarships:
        {matched_df.to_markdown(index=False)}  # Display the filtered scholarships in markdown format
        """

        # Step 8: Generate Chat Response using the OpenAI client
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
            )

            # Debugging: Print the raw response to the app (can be hidden later)
            st.write("**Debug Response:**", response)

            # Extract and display the result
            if "choices" in response and len(response["choices"]) > 0:
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
