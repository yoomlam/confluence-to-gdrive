import streamlit as st

# Define the pages
main_page = st.Page("streamlit_main.py", title="Main Page", icon="🎈")
page_2 = st.Page("streamlit_page2.py", title="Page 2", icon="❄️")
page_3 = st.Page("streamlit_page3.py", title="Page 3", icon="🎉")

# Set up navigation
pg = st.navigation([page_3,page_2,main_page])

# Run the selected page
pg.run()
