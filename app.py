import streamlit as st
from pydantic import BaseModel, Field
from streamlit_autoform import autoform

st.title("Streamlit Autoform: Advanced Features 🚀")

class UserProfile(BaseModel):
    # This field is locked. The user cannot edit "user_89234"
    user_id: str = Field(
        default="user_89234", 
        json_schema_extra={"disabled": True}
    )
    # This shows grayed-out placeholder text before the user types
    social_handle: str = Field(
        default="", 
        json_schema_extra={"placeholder": "@username"}
    )

result = autoform(UserProfile)
if result:
    st.json(result.model_dump())