import pandas as pd
import streamlit as st
from pydantic import ValidationError

from llm_agent.connectors.postgres_connector import PostgresConnector
from llm_agent.connectors.qdrant_connector import QdrantConnector
from llm_agent.member_recommendation import recommend_member_by_id
from llm_agent.src.rerank import reranker_setup

pg_conn = PostgresConnector()
qdrant_conn = QdrantConnector()
reranker = reranker_setup()

from llm_agent.src.utils import Member


def wide_space_default():
    st.set_page_config(layout="wide")

@st.cache_data
def convert_df(df):
    # IMPORTANT: Cache the conversion to prevent computation on every rerun
    return df.to_csv().encode("utf-8")


def update_member_info(member: Member):
    st.write("Received Member object:", member)


def update_member_info_tab():
    st.header("Update Member Information")
    update_qdrant_immediately = st.checkbox("Update data immediately to Vector search engine (`Qdrant`)")
    with st.form("Update member information"):
        member_no = st.number_input("Member number", min_value=1, step=1)
        name = st.text_input("Member name")
        company = st.text_input("Company name")
        title = st.text_input("Title")
        background = st.text_area("Background")
        company_url = st.text_input("Company URL")
        linkedin_url = st.text_input("Linkedin URL")
        versions = {"v1": st.checkbox("v1", value=True), "v2": st.checkbox("v2", value=False)}
        summary = st.text_area("LLM Summary")

        submitted = st.form_submit_button("Validate & Send")
        if submitted:
            try:
                member = Member(
                    member_no=member_no,
                    name=name,
                    company=company,
                    title=title,
                    background=background,
                    company_url=company_url,
                    linkedin_url=linkedin_url,
                    versions=versions,
                    summary=summary
                )
                old_data = pg_conn.get_member_info_by_id(member_no)
                if old_data:
                    st.warning("Member already exists. Please update with new `member_no`.")
                else:
                    pg_conn.update_member_info([member])
                    if update_qdrant_immediately:
                        qdrant_conn.insert_members([member])
            except ValidationError as e:
                st.error(f"Validation error: {e}")

    with st.expander("Upload by Excel File", expanded=False):
        st.write(
            """
            - **Member number**: Unique identifier for each member
            - **Member name**: Name of the member
            - **Company name**: Name of the company
            - **Title**: Job title of the member
            - **Background**: Background information of the member
            - **Company URL**: URL of the company
            - **Linkedin URL**: URL of the LinkedIn profile
            - **Versions**: Check the versions to update the information
            - **LLM Summary**: Summary of the member information
            """
        )
        st.header("Upload Excel File")
        uploaded_file = st.file_uploader("Choose an XLSX file", type="xlsx")
        if uploaded_file is not None:
            try:
                df = pd.read_excel(uploaded_file)
                for idx, row in df.iterrows():
                    try:
                        member = Member(**row.to_dict())
                        old_data = pg_conn.get_member_info_by_id(member.member_no)
                        if old_data:
                            st.warning("Member already exists. Please update with new `member_no`.")
                        else:
                            pg_conn.update_member_info([member])
                            if update_qdrant_immediately:
                                qdrant_conn.insert_members([member])
                    except ValidationError as e:
                        st.error(f"Validation error in row {idx + 1}: {e}")
            except Exception as e:
                st.error(f"Error reading Excel file: {e}")


def member_recommendation_tab():
    st.header("Recommend similar items")
    with st.form("Select member to recommend"):
        target_member_no = st.number_input("Member number", min_value=1, step=1)
        recommendation_version = st.selectbox("Version of LLM pipeline to use", options=["v1", "v2"], index=0)
        res_submitted = st.form_submit_button("Validate & Send")
        if res_submitted:
            res = recommend_member_by_id(target_member_no, recommendation_version)
            df_res = pd.DataFrame([res], index=[1])
            st.write("Recommendation for member:", target_member_no)
            st.table(df_res)

def member_recommendation_bulk():
    st.header("Recommend similar items")
    df_res = None
    with st.form("Select range of member to recommend"):
        target_member_no_start = st.number_input("Member number no start", min_value=1, step=1)
        target_member_no_end = st.number_input("Member number no end", min_value=1, step=1)

        recommendation_version = st.selectbox("Version of LLM pipeline to use", options=["v1", "v2"], index=0)
        res_submitted = st.form_submit_button("Validate & Send")

        if res_submitted:
            index = list(range(target_member_no_start, target_member_no_end+1))
            res = [recommend_member_by_id(i, recommendation_version) for i in index]
            df_res = pd.DataFrame(res, index=index)
    if df_res is not None:
        st.write("Recommendation for member:", target_member_no_start, "to", target_member_no_end)
        st.table(df_res)
        csv = convert_df(df_res)
        st.download_button(label="Download CSV",
                           data=csv,
                           file_name="recommendation.csv",
                           mime="text/csv")

def main():
    st.title("Member Recommendation System")
    rec_tab_all,rec_tab, update_tab = st.tabs(["Member recommendation (by `id` range)", "Member recommendation", "Update data"])
    with rec_tab_all:
        member_recommendation_bulk()
    with rec_tab:
        member_recommendation_tab()
    with update_tab:
        update_member_info_tab()


if __name__ == "__main__":
    wide_space_default()
    main()
