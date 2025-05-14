import logging
import os
import requests
import streamlit as st
from confluence_exporter import ConfluenceExporter

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

if not hasattr(st, 'already_started_server'):
    # https://discuss.streamlit.io/t/streamlit-restful-app/409/2
    # Hack the fact that Python modules (like st) only load once to
    # keep track of whether this file already ran.
    st.already_started_server = True

    st.write('''
        The first time this script executes it will run forever because it's
        running a Flask server.

        Just close this browser tab and open a new one to see your Streamlit
        app.
    ''')

    logger.info("Starting server...")
    from main import app
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 3000)))


st.write("Hello world")


# Add button to query API 
space_key = st.text_input('space key', 'NL')
page_title = st.text_input('page title', 'Design and Prototyping')


def confluence_pages(space_key, page_title):
    logger.debug("space_key=%r, page_title=%r", space_key, page_title)
    exporter = ConfluenceExporter()
    pages = exporter.list_pages(space_key, page_title)
    return [{"title": p["title"], "id": p["id"]} for p in pages]

if st.button('Run direct'):
    response = "response1 placeholder"
    # url = 'http://127.0.0.1:3000/confluence_pages?page_title=Design%20and%20Prototyping'
    # response = requests.get(url)
    response = confluence_pages(space_key, page_title)

    response

st.session_state.api_response = ""
if st.button('Call API'):
    response = "response2 placeholder"
    url = 'http://127.0.0.1:3000/confluence_pages?page_title=Design%20and%20Prototyping'
    response = requests.get(url)
    print(response.json())
    st.session_state.api_response = str(response.json())

st.write(st.session_state.api_response)
