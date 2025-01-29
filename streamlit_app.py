import streamlit as st
import pandas as pd
import openai
import os

st.title("💬 GenOne Scholarship Opportunity Chatbot")

# Load OpenAI API key
openai_api_key = os.getenv("OPENAI_API_KEY")

if not openai_api_key:
    st.error("Please contact Admin for missing OpenAI API key.")
else:
    openai.api_key = openai_api_key  # Set OpenAI API key

client = openai.Client(api_key=openai_api_key)

# Function to parse the response and create a DataFrame
def parse_scholarships(response_content):
    lines = response_content.split("\n")
    scholarships = []

    # Find where the table starts
    table_start = False
    for line in lines:
        if line.startswith("| Scholarship Name"):
            table_start = True
            continue
        if table_start and line.startswith("|"):
            parts = [x.strip() for x in line.split("|")[1:-1]]  # Split and remove empty parts
            if len(parts) == 5:  # Ensure it's a valid row
                scholarships.append(parts)

    # Convert to DataFrame
    df = pd.DataFrame(
        scholarships,
        columns=["Scholarship Name", "Scholarship Website", "Deadline Status", "Amount", "Requirements"]
    )

    return df

# User query input
if user_query := st.chat_input("What kind of scholarship opportunities are you looking for?"):
    
    # Prepare the prompt for OpenAI API
    prompt = f"""
    ### Objective
    The chatbot assists users in discovering relevant opportunities by querying the provided data. Responses should include:
    - Relevant details about matching opportunities, including name, website, deadline, requirements, etc.
    - A user-friendly display, with tables for multiple matches.
    - Clarity, friendliness, and professionalism.
    - Make sure to look through the full data and provide all the matching responses.

    ### User Query
    {user_query}
    """

    # Generate Chat Response using OpenAI API
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )

    # Extract response content
    response_content = response.choices[0].message.content

    # Debug: Print raw response
    st.write("### OpenAI Response Debug")
    st.write("##### Response should be in the Choices row, double-click to see")
    st.dataframe(response)

    # Parse the response into a structured table
    df_scholarships = parse_scholarships(response_content)

    # Display the scholarships table
    st.write("### Matching Scholarship Opportunities")
    st.dataframe(df_scholarships)
