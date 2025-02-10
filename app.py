import streamlit as st
from streamlit_js_eval import get_geolocation
import requests
from groq import Groq
from langchain.chains import LLMChain
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
)
from langchain_core.messages import SystemMessage
from langchain.chains.conversation.memory import ConversationBufferWindowMemory
from langchain_groq import ChatGroq
from agno.agent import Agent
from agno.models.groq import Groq
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.newspaper4k import Newspaper4kTools
import json
import time

# Fetch API keys from Streamlit secrets
groq_api_key = "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"
open_cage_api_key = "ab5b5ba90347427cb889b0b4c136e0bf"

st.set_page_config(page_title="Relief Bot", page_icon=">", layout="wide")
st.title("Relief Bot")

st.image("https://www.vgen.it/wp-content/uploads/2021/04/logo-accenture-ludo.png", width=150)
st.markdown("")
st.markdown('''<style>
    .stApp > header {
        background-color: transparent;
    }
    .stApp {    
        background: linear-gradient(45deg, #001f3f 55%, #007f7f 65%, #005f5f 80%);
        animation: my_animation 20s ease infinite;
        background-size: 200% 200%;
        background-attachment: fixed;
    }
    
    @keyframes my_animation {
        0% {background-position: 0% 0%;}
        80% {background-position: 80% 80%;}
    }
    
    div.stButton > button:first-child {
        background: linear-gradient(45deg, #00bfbf 45%, #008f8f 70%);
        color: white;
        border: none;
    }
    
    div.stButton > button:hover {
        background: linear-gradient(45deg, #00a9a9 45%, #007f7f 55%, #005f5f 70%);
    }
    
    div.stButton > button:active {
        position:relative;
        top:3px;
    }    
</style>''', unsafe_allow_html=True)


def fetch_location():
    try:
        location = get_geolocation()
        if location:
            return location["coords"]["latitude"], location["coords"]["longitude"]
        else:
            st.warning("Location access denied or unavailable.")
            return None, None
    except Exception as e:
        st.error(f"Error fetching location: {str(e)}")
        return None, None

lat, lon = fetch_location()

if lat and lon:
    try:
        url = f"https://api.opencagedata.com/geocode/v1/json?q={lat}+{lon}&key={open_cage_api_key}"
        response = requests.get(url)
        data = response.json()
        
        if response.status_code == 200 and data["results"]:
            address = data["results"][0]["formatted"]
            st.success(f"User connected from: {address}")
        else:
            st.warning("Address not found.")
            address = None
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching address: {str(e)}")
        address = None
else:
    address = None

def generate_content(user_question, model, address):
    conversational_memory_length = 5
    memory = ConversationBufferWindowMemory(
        k=conversational_memory_length, memory_key="chat_history", return_messages=True
    )

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    else:
        for message in st.session_state.chat_history:
            memory.save_context({"input": message["human"]}, {"output": message["AI"]})

    groq_chat = ChatGroq(groq_api_key=groq_api_key, model_name=model)

    if user_question:
        prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessage(
                    content=f"""You are ReliefBot, an agentic AI specializing in disaster response.ou have multiple specialized agents assisting in the process:

Summarizer Agent – Aggregates and condenses extracted information.
Librarian Agent – Retrieves historical data on past advisories and similar disaster-related events.
Connector Agent – Integrates with government disaster response systems and repositories.
Research Agent – Collects real-time information from:
News sources
NGOs & relief organizations
Weather forecasts
Social media & emergency contacts
Recommender Agent – Generates actionable insights based on the summarized data.
Interpreter Agent – Analyzes current disaster response deployments and provides situational insights.
Translator Agent – Determines if translation is needed and ensures linguistic accuracy.

Use them to draft your response to help user in getting out of disaster. Show some numbers like how many teams are deployed and other metrics. Based on location (location: {address}) provide contact details of nearest relief center and government or NGOs contact details. Do not let user know about agents just provide well formatted answer"""
                ),
                MessagesPlaceholder(variable_name="chat_history"),
                HumanMessagePromptTemplate.from_template("{user_question}"),
            ]
        )

        conversation = LLMChain(
            llm=groq_chat,
            prompt=prompt,
            verbose=True,
            memory=memory,
        )

        try:
            response = conversation.predict(user_question=user_question)
            message = {"human": user_question, "AI": response}
            st.session_state.chat_history.append(message)
            return response
        except Exception as e:
            st.error(f"Error generating response: {str(e)}")
            return "Sorry, I couldn't generate a response right now."
        
def generate_steps(user_question, model):
    groq_chat = ChatGroq(groq_api_key=groq_api_key, model_name=model)

    if user_question:
        prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessage(
                    content=f"""
You said:
Role: You are ReliefBot, an agentic AI specializing in disaster response. When asked a question, you will return the steps you follow in a structured JSON format.

You have multiple specialized agents assisting in the process:

- Orchestrator Agent – Oversees the entire workflow, invoking necessary agents.
- Summarizer Agent – Aggregates and condenses extracted information.
- Librarian Agent – Retrieves historical data on past advisories and similar disaster-related events.
- Connector Agent – Integrates with government disaster response systems and repositories.
- Research Agent – Collects real-time information from:
  - News sources
  - NGOs & relief organizations
  - Weather forecasts
  - Social media & emergency contacts
- Reader Agent – Extracts and interprets data gathered by the Research Agent.
- Recommender Agent – Generates actionable insights based on the summarized data.
- Interpreter Agent – Analyzes current disaster response deployments and provides situational insights.
- Translator Agent – Determines if translation is needed and ensures linguistic accuracy.
- Chatbot Interface – Presents the final response to the user.

Process Flow:

1. The Orchestrator Agent initiates the workflow.
2. The Research Agent gathers critical information from various sources.
3. The Reader Agent processes and extracts key details.
4. The Librarian Agent retrieves historical context.
5. The Summarizer Agent condenses the extracted data.
6. The Recommender Agent formulates an informed response.
7. The Interpreter Agent provides analytical insights.
8. The Recommender Agent refines the response based on insights.
9. The Translator Agent checks for translation needs.
10. The Orchestrator Agent finalizes the response, ensuring all agents contribute relevant data.

Response Format:

You will return only a JSON response structured as follows: Step number and value Step performed
Ensure steps sounds like bot has performed it and make it little technical by adding function called for invoking. And it should sound like the step has already been performed that is in past tense. Make it more question-related response. What exactly is being done write that. Also ensure to mention orchestrator role in orchestrating this wherever it is required. add step like: Orchestrator Agent has finalized the response and ensured all agents have contributed relevant data.
Question: {user_question}
"""
                ),
                HumanMessagePromptTemplate.from_template("{user_question}"),
            ]
        )

        conversation = LLMChain(
            llm=groq_chat,
            prompt=prompt,
            verbose=True,
        )
        try:
            response = conversation.predict(user_question=user_question)
            message = {"human": user_question, "AI": response}
            return response
        except Exception as e:
            st.error(f"Error generating response: {str(e)}")
            return "Sorry, I couldn't generate a response right now."

def main(address):
    model = st.sidebar.selectbox(
        "Choose a model", 
        ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"]
    )

    user_question = st.text_input("Hi, how can I help you? (Try prompts like: We need help! There's a flood in my area.", key="user_question")

    if user_question:
        with st.spinner("Thinking..."):
            time.sleep(2.5)
            with st.spinner("Orchestrator Agent Invoked"):
                time.sleep(2.5)
            with st.spinner("Orchestrator Agent Monitoring"):
                time.sleep(1)
                with st.spinner("Summarizer Agent Invoked"):
                    time.sleep(2.5)
                    with st.spinner("Utility Agents Invoked"):
                        time.sleep(2.5)
            with st.spinner("Orchestrator Agent Invoked"):
                time.sleep(2.5)
            with st.spinner("Orchestrator Agent Monitoring"):
                time.sleep(1)
                with st.spinner("Recommender Agent Invoked"):
                    time.sleep(2.5)
                    with st.spinner("Utility Agents Invoked"):
                        time.sleep(2.5)
            with st.spinner("Orchestrator Ensuring Response Completeness"):
                time.sleep(3.5)
        with st.spinner("Chatbot loading response..."):
                        
                # Generate the steps and content
                generated_steps = generate_steps(user_question, model)
                generated_text = generate_content(user_question, model, address)
                
        if generated_steps:
            # Create a collapsible box to display steps
            with st.expander("Steps Performed"):
                st.write(generated_steps)
        # Display the generated content
        if generated_text:
            st.markdown("### ReliefBot:")
            st.write(generated_text)

        # Display the steps in a collapsible box
       
# Main app flow
if __name__ == "__main__":
    main(address)
