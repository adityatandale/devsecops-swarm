"""Streamlit control room: live incident timeline, diffs, sandbox output."""
import subprocess
import sys

import streamlit as st

from swarm.config import ROOT
from swarm.store import list_runs

st.set_page_config(page_title="Self-Healing DevSecOps Swarm", page_icon="🛡️", layout="wide")
st.title("🛡️ Self-Healing Multi-Agent DevSecOps Engineer")

with st.sidebar:
    st.header("Controls")
    if st.button("💥 Inject demo crash"):
        subprocess.run([sys.executable, "-m", "swarm.simulate"], cwd=ROOT)
        st.success("Crash written to demo_service/logs/app.log")
    sandbox = st.selectbox("Sandbox", ["docker", "local"])
    if st.button("🚀 Run swarm now"):
        with st.spinner("Agents working..."):
            r = subprocess.run([sys.executable, "main.py", "run", "--force", "--sandbox", sandbox],
                               cwd=ROOT, capture_output=True, text=True)
        st.code(r.stdout[-3000:] + r.stderr[-1500:])
    st.caption("Refresh the page to see new runs.")

runs = list_runs()
if not runs:
    st.info("No runs yet. Inject a crash, then run the swarm.")
    st.stop()

c1, c2, c3 = st.columns(3)
c1.metric("Incidents handled", len(runs))
c2.metric("PRs prepared", sum(r.get("status") == "pr_submitted" for r in runs))
c3.metric("Escalated", sum(r.get("status") == "escalated" for r in runs))

labels = [f"{r['file']} - {r.get('status')}" for r in runs]
run = runs[labels.index(st.selectbox("Select run", labels))]

if inc := run.get("incident"):
    st.subheader(f"Incident `{inc['id']}` - {inc['exception_type']}: {inc['exception_message']}")
    st.caption(f"Signature: {inc['signature']}")
tab1, tab2, tab3, tab4 = st.tabs(["Agent timeline", "Patch diff", "Attempts & sandbox", "Similar fixes (Qdrant)"])
with tab1:
    for e in run.get("events", []):
        st.markdown(f"`{e['t']}` **{e['agent']}** - {e['msg']}")
with tab2:
    if run.get("patch"):
        st.code(run["patch"]["diff"], language="diff")
    else:
        st.write("No patch produced.")
with tab3:
    for a in run.get("attempts", []):
        st.markdown(f"**Attempt {a['n']}** - {'✅ passed' if a.get('passed') else '❌ failed'}")
        st.code(a.get("test_output", ""), language="text")
with tab4:
    st.json(run.get("similar_fixes", []))
