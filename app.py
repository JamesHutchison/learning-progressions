import json
from pathlib import Path

import streamlit as st
import streamlit_chat as st_chat
from langchain import chat_models
from langchain.prompts.chat import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)
from langchain.schema import HumanMessage, SystemMessage

if "chat_history" not in st.session_state:
    # chat history used for display
    st.session_state["chat_history"] = []

st.title("Create learning progressions")


@st.cache_data
def get_api_key() -> str:
    api_key_path = Path(".api_key")
    if api_key_path.exists():
        incoming_api_key = api_key_path.read_text().strip()
    else:
        incoming_api_key = ""
    return incoming_api_key


def api_key_change():
    if len(st.session_state["open_ai_key"]) == 51:
        st.session_state["valid_api_key"] = True
    else:
        st.session_state["valid_api_key"] = False


api_key = st.sidebar.text_input(
    "OpenAI API Key",
    key="open_ai_key",
    type="password",
    value=get_api_key(),
    max_chars=51,
    on_change=api_key_change,
).strip()


st.session_state["valid_api_key"] = len(st.session_state["open_ai_key"]) == 51

standard = st.text_input(
    "Create learning progressions for this standard", key="standard", max_chars=200
)

more_info = st.text_area(
    "More information and context for the AI to consider",
    key="more_info",
    max_chars=2000,
    height=200,
)
chat_response = None

if not st.session_state.get("valid_api_key", False):
    st.write(
        ":red[API Key missing. Add it on the left sidebar. On mobile expand it on the top left]"
    )


# feels janky but without this the "start" button doesn't disable / hide properly
if "should_do_first_chat" not in st.session_state:
    st.session_state["should_do_first_chat"] = False


def do_chat():
    chat = chat_models.ChatOpenAI(
        model_name="gpt-4", temperature=0.2, openai_api_key=api_key, max_tokens=1500
    )
    chat_history = st.session_state["chat_history"]
    print(chat_history)
    messages = [
        HumanMessage(content=msg) if is_user else SystemMessage(content=msg)
        for (msg, is_user) in chat_history
    ]
    return chat(
        messages
        + [
            SystemMessage(
                content="Only respond to the most recent user message. Be short and succinct."
            )
        ]
    )


if st.session_state["should_do_first_chat"]:
    st.session_state["should_do_first_chat"] = False
    response = do_chat()
    chat_response = response.content
    # st.session_state["chat_history"].append((chat_response, False))

    json_object_start = chat_response.find("{")
    json_object_end = chat_response.rfind("}")
    json_object = chat_response[json_object_start : (json_object_end + 1)]
    st.session_state["raw_response"] = chat_response
    try:
        st.session_state["values"] = json.loads(json_object)
    except Exception:
        print(f"JSON object: {json_object}")
        import traceback

        traceback.print_exc()
        st.write("Failed to load ouput. Check raw response")
    st.session_state["chat_history"].append(("Done!", False))


system_message_prompt = SystemMessagePromptTemplate.from_template(
    "You are an elementary school instructor tasked with creating a playbook for students. "
    "The playbook is based off of a learning standard. The playbook needs to build a list of "
    "concepts (nouns) and skills (verbs). It will also have a learning progression."
)

first_prompt_template = (
    "We will create a learning progression for the standard: {standard}\n"
    "Additional information to consider: {more_info}\n"
    "First, reason through the concepts and skills based on the standard. "
    "For only this step, concepts and skills should be sentences, not single words. "
    "Avoid concepts and skills that make no sense without further context. "
    "These are concepts and skills students would be formally taught. "
    "An example of a bad concept is 'math'. An example of a bad skill is 'learning', 'determining', 'explaining'. "
    "If a skill is teachable as a single word, then exclude it. "
    "After reasoning, produce the list of concepts and skills. Keep this list concise. "
    "Then, create a learning progression. The learning progression "
    "is a list of concepts and skills that progressively drive the student towards the learning "
    "goals. List these in increasing complexity. The easier learnings should be a foundation for the later ones. "
    "Steps in the learning progression should not be the same as a prior one. "
    "Next, take the role of a school principal and criticize the concepts, skills, and learning progression. "
    "Evaluate whether our earlier rules are clearly being followed. Suggest changes. Ensure ambiguous statements, "
    "are expanded upon. Suggest deletions for duplicates. "
    "This should be defined such that someone with little experience can understand what it means. "
    "After that is generated, create a final version of the list of concepts and skills as well "
    "as the learning progression. Produce a correct JSON object with the keys "
    "'concepts_and_skills' and 'learning_progression'. The concepts and skills should be a list of size 2. The first "
    "item is the concept or skill, which is a noun or verb. The second item is why it is relevant."
)
prompt_template_expander = st.expander("prompt template")
with prompt_template_expander:
    user_prompt_template = st.text_area(
        "prompt template", first_prompt_template, height=200, label_visibility="hidden"
    )

if not st.session_state.get("hide_start_button", False) and st.session_state["valid_api_key"]:
    start_pressed = st.button("Start", key="started")
    if start_pressed and standard:
        st.session_state["hide_start_button"] = True
else:
    start_pressed = False

if start_pressed and standard:
    first_prompt = HumanMessagePromptTemplate.from_template(user_prompt_template)
    chat_prompt = ChatPromptTemplate.from_messages([system_message_prompt, first_prompt])
    chat_prompt_value = chat_prompt.format_prompt(
        standard=standard, more_info=(more_info or "no extra info")
    )

    st.session_state["chat_history"] = []
    system_message, user_message = chat_prompt_value.to_messages()
    st.session_state["chat_history"].append((system_message.content, False))
    st.session_state["chat_history"].append((user_message.content, True))

    st.session_state["should_do_first_chat"] = True

if st.session_state.get("raw_response"):
    with st.expander("Raw response"):
        st.write(st.session_state["raw_response"])

if st.session_state.get("values"):
    concepts_and_skills = st.session_state["values"]["concepts_and_skills"]
    learning_progression = st.session_state["values"]["learning_progression"]

    st.write("Concepts and skills:")
    st.write(concepts_and_skills)

    st.write("Learning progression:")
    st.write(learning_progression)


chat_history_container = st.container()

if st.session_state.get("chat_history"):
    with chat_history_container:
        for i, (message, is_user) in enumerate(st.session_state["chat_history"]):
            st_chat.message(message, is_user=is_user, key=i)

if st.session_state.get("raw_response"):
    with st.form(key="follow_up", clear_on_submit=True):
        user_input = st.text_area("Follow up:", key="input", height=100)
        submit_button = st.form_submit_button(label="Send")

    if submit_button and user_input:
        st.session_state["chat_history"].append((user_input, True))
        with chat_history_container:
            st_chat.message(user_input, is_user=True)
        # st.session_state["messages"].append(HumanMessage(content=user_input))

        output = do_chat()
        st.session_state["chat_history"].append((output.content, False))
        with chat_history_container:
            st_chat.message(output.content, is_user=False)

if st.session_state["should_do_first_chat"]:
    st.rerun()
