import streamlit as st
import numpy as np
import pandas as pd
import time
from datetime import datetime, timedelta

st.write("Page 2 for testing")
ss = st.session_state

st.markdown("# Test page")
st.sidebar.markdown("## Test page 🎈")

# Add a placeholder
# latest_iteration = st.empty()
# bar = st.progress(0)
# for i in range(0, 101, 5):
#     # Update the progress bar with each iteration.
#     latest_iteration.text(f'Iteration {i+1}')
#     bar.progress(i)
#     time.sleep(0.01)
# '...and now we\'re done!'

# if "df" not in ss:
#     ss.df = pd.DataFrame(np.random.randn(15, 3), columns=(["A", "B", "C"]))
# my_data_element = st.line_chart(ss.df)

# if st.button("Set A=0"):
#     # df2=my_data_element.dataframe()
#     # df2
#     "Setting A to zeros"
#     ss.df.loc[ss.df['A']<10,'A']=0
#     # Rerun to update line_chart that was previously rendered
#     st.rerun()
#     # for tick in range(10):
#     #     time.sleep(.5)
#     #     add_df = pd.DataFrame(np.random.randn(1, 3), columns=(["A", "B", "C"]))
#     #     my_data_element.add_rows(add_df)
# # st.line_chart(ss.df)
# # ss.df


# @st.fragment
# def fragment_function():
#     # When a user interacts with an input widget inside a fragment,
#     # only the fragment reruns instead of the full script.
#     if st.button("Set B=0"):
#         st.write("Setting B")
#         ss.df.loc[ss.df['B']<10,'B']=0
#     st.line_chart(ss.df)

# fragment_function()

## https://docs.streamlit.io/develop/tutorials/execution-flow/start-and-stop-fragment-auto-reruns

def get_recent_data(last_timestamp):
    """Generate and return data from last timestamp to now, at most 60 seconds."""
    now = datetime.now()
    if now - last_timestamp > timedelta(seconds=60):
        last_timestamp = now - timedelta(seconds=60)
    sample_time = timedelta(seconds=0.5)  # time between data points
    next_timestamp = last_timestamp + sample_time
    timestamps = np.arange(next_timestamp, now, sample_time)
    sample_values = np.random.randn(len(timestamps), 2)

    data = pd.DataFrame(sample_values, index=timestamps, columns=["A", "B"])
    return data

if "data" not in ss:
    ss.data = get_recent_data(datetime.now() - timedelta(seconds=60))
if "stream" not in ss:
    ss.stream = False

def toggle_streaming():
    ss.stream = not ss.stream

st.sidebar.slider(
    "Check for updates every: (seconds)", 0.5, 5.0, value=1.0, key="run_every"
)

st.button(
    "Start streaming", disabled=ss.stream, on_click=toggle_streaming
)
st.button(
    "Stop streaming", disabled=not ss.stream, on_click=toggle_streaming
)

if ss.stream is True:
    run_every = ss.run_every
else:
    run_every = None

f"run_every = {run_every} {ss.run_every}"

@st.fragment(run_every=run_every)
def show_latest_data():
    last_timestamp = ss.data.index[-1]
    ss.data = pd.concat(
        [ss.data, get_recent_data(last_timestamp)]
    )
    # ss.data = ss.data[-100:]
    st.line_chart(ss.data)
    toggle_streaming()
    st.rerun()

if ss.stream:
    show_latest_data()



if False and not hasattr(st, "already_started_server"):
    # https://discuss.streamlit.io/t/streamlit-restful-app/409/2
    # Hack the fact that Python modules (like st) only load once to
    # keep track of whether this file already ran.
    st.already_started_server = True

    st.write(
        """
        The first time this script executes it will run forever because it's
        running a Flask server.

        Just close this browser tab and open a new one to see your Streamlit
        app.
    """
    )

    logger.info("Starting server...")
    from api import app

    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 3000)))

# Test code that calls API instead of using main.py
if hasattr(st, "already_started_server"):
    ss.api_response = ""
    if st.button("Call API"):
        response = "response2 placeholder"
        url = "http://127.0.0.1:3000/confluence_pages?page_title=Design%20and%20Prototyping"
        response = requests.get(url)
        print(response.json())
        ss.api_response = str(response.json())
    st.write(ss.api_response)
