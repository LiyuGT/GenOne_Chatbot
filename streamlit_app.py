import streamlit as st
import pandas as pd
import openai
import os


# Function to estimate the number of tokens in a string
def num_tokens_from_string(string: str) -> int:
   """Estimate the number of tokens in a string by using a simple heuristic (approx 4 tokens per word)."""
   # Heuristic: approximate that each word is about 4 tokens in the GPT-4 model
   return len(string.split()) * 4


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


# OpenAI API client using the provided API key
client = openai.Client(api_key=openai_api_key)


# Load the Excel file
@st.cache_data
def load_data():
   file_path = "Scholarships Export for Chatbot.xlsx"  # Ensure the file is uploaded
   if not os.path.exists(file_path):
       st.error(f"File not found: {file_path}")
       st.stop()


   # Read the file
   df = pd.read_excel(file_path)
   df = df.applymap(lambda x: str(x).strip() if isinstance(x, str) else x)


   # Replace empty cells in "School (if specific)" with "none"
   df["School (if specific)"] = df["School (if specific)"].fillna("none")


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


# Add demographic dropdown only if "none" is selected
if selected_school == "none":
   # Replace NaN values with "none" before extracting unique options
   df["Demographic focus"] = df["Demographic focus"].fillna("none")
  
   # Extract unique demographic options (including "none")
   demographic_options = sorted(df["Demographic focus"].unique())


   # Create a dropdown with only the available demographic options
   selected_demographic = st.selectbox("Select your demographic group:", demographic_options)
else:
   selected_demographic = None  # No demographic filtering when a school is selected


# Chatbot Logic (stores all previous user messages)
if "messages" not in st.session_state:
   st.session_state.messages = []


for message in st.session_state.messages:
   with st.chat_message(message["role"]):
       st.markdown(message["content"])


# Set response to none (removes the error)
response = None


# Wait for the user's query
if user_query := st.chat_input("What kind of scholarship opportunities are you looking for?"):


   # Add the user query to the session state
   st.session_state.messages.append({"role": "user", "content": user_query})
   with st.chat_message("user"):
       st.markdown(user_query)


   # Filter data based on selected school
   if selected_school == "none":
       filtered_data = df[df["School (if specific)"] == "none"]
       # Apply demographic filter if "All" is not selected
       if selected_demographic and selected_demographic != "All":
           filtered_data = filtered_data[filtered_data["Demographic focus"] == selected_demographic]
   else:
       filtered_data = df[df["School (if specific)"] == selected_school]


   # Convert filtered data to string for token estimation
   filtered_data_string = filtered_data.to_string(index=False)
   token_count = num_tokens_from_string(filtered_data_string)


   # If tokens exceed 10,000, limit to 20 rows
   if token_count > 10000:
       filtered_data = filtered_data.head(20)
   else:
       filtered_data = filtered_data  # Use all rows


   # Convert final filtered data to string for OpenAI
   filtered_data_string = filtered_data.to_string(index=False)


   # Prepare the prompt for OpenAI API
   prompt = f"""
   ### Objective
   The chatbot assists users in discovering relevant opportunities by querying the provided data. Responses should include:
   - Relevant details about matching opportunities, including name, website, deadline, requirements, etc.
   - A user-friendly display, with tables for multiple matches.
   - ### Table Format Example: | Scholarship Name | Amount | Requirements | Scholarship Website | Deadline Status |
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


   # Extract response content safely
   if response and hasattr(response, "choices"):
       response_content = response.choices[0].message.content
   else:
       response_content = "No response received from OpenAI."


   # Function to parse response into structured format
   def parse_scholarships(response_content):
       lines = response_content.strip().split("\n")
       scholarships = []


       for line in lines:
           parts = line.split("|")
           if len(parts) >= 5:
               scholarships.append([p.strip() for p in parts[1:-1]])  # Remove empty parts


       if scholarships:
           df_scholarships = pd.DataFrame(scholarships[1:], columns=scholarships[0])  # First row as headers
           return df_scholarships
       return pd.DataFrame(columns=["Scholarship Name", "Amount", "Requirements", "Scholarship Website", "Deadline Status"])  # Ensure empty DF has correct headers


   # Parse response into a structured table
   df_scholarships = parse_scholarships(response_content)


   if df_scholarships.empty:
       st.write("No scholarships found matching your query.")
   else:
       st.write("### Matching Scholarship Opportunities")
       st.dataframe(df_scholarships)



