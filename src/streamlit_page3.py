import streamlit as st
import numpy as np
import pandas as pd
import time
from datetime import datetime, timedelta

st.write("Page 3 for testing")
ss = st.session_state

st.markdown("# Test page 3")
st.sidebar.markdown("## Test page 3 🎈")

## https://docs.streamlit.io/develop/concepts/design/multithreading

from threading import Thread
import random
import queue

if "data_queues" not in ss:
    ss.data_queues = [queue.Queue() for _ in range(5)]
    ss.delays = [random.uniform(1, 5) for _ in range(5)]
    ss.thread_lives = [False] * len(ss.delays)

st.write(ss.data_queues)

empty_container = st.empty()
# if any(ss.thread_lives):
#     st.write(f"{sum(ss.thread_lives)} Threads running")
empty_container.write(f"{sum(ss.thread_lives)} Threads running")

bar = st.progress(1.0-(sum(ss.thread_lives)/len(ss.thread_lives)))

frag_container = st.container()

if "stream" not in ss:
    ss.stream = False

def start_threads():  # any(ss.thread_lives)):
    class WorkerThread(Thread):
        def __init__(self, id, delay, data_queue):
            super().__init__()
            self.id = id
            self.delay = delay
            self.return_value = None
            self.q = data_queue

        def run(self):
            start_time = time.time()
            for item in range(5):
                # item = random.randint(1, 100)
                print(f"Producer {self.id}: produced item {item}")
                self.q.put(f"{self.id}: {item}")
                time.sleep(random.uniform(1, 2))
            sleep_time = self.delay - (time.time() - start_time)
            time.sleep(max(0, sleep_time))
            # self.q.put(None)  # Sentinel value to signal consumer to exit
            end_time = time.time()
            self.return_value = f"start: {start_time}, end: {end_time}"

    ss.threads = [WorkerThread(i, delay, queue) for i, (delay, queue) in enumerate(zip(ss.delays, ss.data_queues))]
    for thread in ss.threads:
        thread.start()
    ss.thread_lives = [True] * len(ss.delays)

    # ss.stream = True


# Gotcha: Use the `on_click=` callback (rather than `if st.button(...):`) to disable/refresh the button after a click
# https://discuss.streamlit.io/t/streamlit-button-disable-enable/31293
# https://docs.streamlit.io/develop/api-reference/caching-and-state/st.session_state#use-callbacks-to-update-session-state
st.button("Run threads", disabled=any(ss.thread_lives), on_click=start_threads)

st.sidebar.slider(
    "Check for updates every: (seconds)", 0.5, 5.0, value=1.0, key="update_every"
)

if any(ss.thread_lives):
    update_every = ss.update_every
else:
    update_every = None

f"update_every = {update_every}. {ss.update_every}"


result_containers = []
for i, delay in enumerate(ss.delays):
    st.header(f"Thread {i} (delay: {delay})")
    result_containers.append(st.container())

@st.fragment(run_every=update_every)
def update_status():
    # frag_container.write("frag update_status")
    if "threads" not in ss:
        return
    # frag_container.write(f"{update_every} {ss.update_every}")
    for i, thread in enumerate(ss.threads):
        if ss.thread_lives[i]:
            if thread.is_alive():
                data_queue = ss.data_queues[i]
                while not data_queue.empty():
                    item = data_queue.get()
                    if item:
                        result_containers[i].write(f"item: {item}")
                    else:
                        result_containers[i].write(f"Error in thread! Use threading.excepthook to catch it")
            else:
                result_containers[i].write(thread.return_value)
                ss.thread_lives[i] = False

    empty_container.write(f"{sum(ss.thread_lives)} Threads running")
    bar.progress(1.0-(sum(ss.thread_lives)/len(ss.thread_lives)))
    # empty_container.button("Run threads", disabled=any(ss.thread_lives))

    if not any(ss.thread_lives):
        # https://docs.streamlit.io/develop/tutorials/execution-flow/trigger-a-full-script-rerun-from-a-fragment
        st.rerun()  # To update update_every, but it also clears the result_containers

    st.write(st.session_state)

if any(ss.thread_lives):
    update_status()

