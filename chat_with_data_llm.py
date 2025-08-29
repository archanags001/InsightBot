import streamlit as st
import streamlit as st
import os
import google.generativeai as genai
import pandas as pd
import json
import plotly.express as px
from pycaret.datasets import get_data
 # Page setup
st.set_page_config(
    page_title="InsightBot",
    page_icon="📊",
)

GOOGLE_API_KEY = st.secrets['GOOGLE_API_KEY']
genai.configure(api_key=GOOGLE_API_KEY)

def upload_and_preview_data():
    uploaded_file = st.file_uploader("Choose a file (CSV or Excel)", key="file_uploader", type=["csv","xlsx"])

    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                try:
                    df = pd.read_csv(uploaded_file)
                except Exception as e:
                    st.error(str(e))
            elif uploaded_file.name.endswith(('.xlsx', '.xls')):
                try:
                    df = pd.read_excel(uploaded_file)
                except Exception as e:
                    st.error(str(e))
            # st.write("Data Preview:")
            # st.write(df)
            return df
        except Exception as e:
            st.error(f"Error reading file: {e}")
    return st.session_state.df


def select_sample_data_page():
    st.subheader("Select a Sample Dataset")
    sample_data_options = ["iris", "wine", "boston", "diabetes", "heart",
                           "titanic", "energy", "airline", "traffic", "concrete", ]
    st.session_state.dataset_name = st.selectbox("Choose a dataset", sample_data_options)

    # if st.button("Load Dataset"):
    if st.session_state.dataset_name == "airline":
        data = pd.DataFrame(get_data(st.session_state.dataset_name))
        data = data.reset_index()
    else:
        data = get_data(st.session_state.dataset_name)

    if data is not None:
        return data
    else:
        st.write("Select a Sample Dataset")
def main():
    st.title("InsightBot")
    st.empty()
    st.markdown("###### InsightBot allows you to chat with your data "
                "using [Google Gemini-1.5-Flash-Latest](https://deepmind.google/technologies/gemini/flash/). "
                "If you don't have your own data to explore, feel free to choose from any of the sample datasets "
                "and start chatting with the data.")
    st.empty()
    if 'df' not in st.session_state:
        st.session_state.df = None
    st.markdown("#### Do you have your own data?")
    file_or_not = st.radio("", ["Yes", "No"])
    if file_or_not == "Yes":
        st.session_state.df = upload_and_preview_data()
    elif file_or_not == "No":
        st.session_state.df = select_sample_data_page()

    if st.session_state.df is not None:
        df = st.session_state.df
        st.write("## Data Preview:")
        st.dataframe(df)

        if "messages" not in st.session_state:
            st.session_state["messages"] = [{"role": "assistant", "content": "Hi , How can I help you?"}]
        elif "messages" in st.session_state:
            st.session_state["messages"] = []

        for msg in st.session_state.messages:
            st.chat_message(msg["role"]).write(msg["content"])


        if user_query := st.chat_input():
            st.chat_message("user").write(user_query)
            system_instruction = f"Analyze this data: {df} \n\nQuestion: {user_query}"
            model = genai.GenerativeModel('gemini-2.5-flash', system_instruction=system_instruction)
            prompt = (f"If the answer requires generating code, include it in the response. "
                        f"Format the code in a JSON object under the key 'code' and text response under the key 'answer' . For example, if the user asks to "
                        f"plot a bar chart for column A, the JSON output should include the necessary pandas code "
                        f"without print statements, like this: dict('code': 'pandas code here').If no code generated then return JSON object dict('answer': 'generated answer','code':''). Use Plotly for any "
                        f"visualizations and assign to fig and must display all figures in streamlit tabs no need to set set_page_config and sidebars. "
                        f"There is no need to include read data from a file as you already have the data as df."
                        f"make sure code will work")
            response = model.generate_content(prompt,
                                              generation_config=genai.GenerationConfig(
                                                  response_mime_type="application/json",
                                                  temperature=0.3,
                                              ),
                                              safety_settings={
                                                  'HATE': 'HARM_BLOCK_THRESHOLD_UNSPECIFIED',
                                                  'HARASSMENT': 'HARM_BLOCK_THRESHOLD_UNSPECIFIED',
                                                  'SEXUAL': 'HARM_BLOCK_THRESHOLD_UNSPECIFIED',
                                                  'DANGEROUS': 'HARM_BLOCK_THRESHOLD_UNSPECIFIED'
                                              }
                                              )

            try:
                answer = json.loads(response.text)["answer"]
                code = json.loads(response.text)['code']
                if answer:
                    st.chat_message("assistant").write(answer)
                if code:
                    st.code(code)
                    try:
                        exec(code)
                    except:
                        st.empty()
                if not answer and not code:
                    try:
                        search_string = '{"answer": "'
                        start_index = response.text.find(search_string)

                        if start_index != -1:
                            # Extract the information after the search_string
                            result = response.text[start_index + len(search_string):]
                            st.chat_message("assistant").write(result)
                    except :
                        st.empty()
            except Exception as e:
                st.error(f"Sorry, no information was generated. Please try again or rephrase your question: {str(e)}")
                st.write(response.candidates[0].safety_ratings)

if __name__ == "__main__":
    main()
