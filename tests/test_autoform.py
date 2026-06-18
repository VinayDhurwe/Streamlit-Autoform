import os
import pytest
from streamlit.testing.v1 import AppTest

# Get the absolute path of the project root (one folder up from the tests/ directory)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# We inject sys.path.insert so the temporary app knows where to find our local package
BASIC_APP_CODE = f"""
import sys
sys.path.insert(0, "{PROJECT_ROOT}")

import streamlit as st
from pydantic import BaseModel, Field
from streamlit_autoform import autoform

class TestModel(BaseModel):
    name: str = Field(default="", min_length=2)
    # Remove 'ge=18' just for this test so we can test Pydantic's internal validation, 
    # OR use a custom Pydantic validator that Streamlit doesn't natively map to a widget.
    age: int = Field(default=20) 

result = autoform(TestModel, submit_label="SubmitForm")
if result:
    # Let's add manual Pydantic validation logic here if autoform doesn't do it automatically
    st.text(f"Success: {{result.name}} is {{result.age}}")
"""

def test_successful_form_submission():
    """Test that valid inputs successfully return the populated model."""
    at = AppTest.from_string(BASIC_APP_CODE)
    at.run()
    
    # 1. Verify the initial state (widgets exist, success text does not)
    assert len(at.text_input) == 1
    assert len(at.number_input) == 1
    assert len(at.button) == 1
    assert len(at.text) == 0 # No success message yet
    
    # 2. Fill out the form via the AppTest API
    at.text_input[0].input("Vinay").run()
    at.number_input[0].set_value(25).run()
    
    # 3. Click the submit button
    at.button[0].click().run()
    
    # 4. Verify the successful output was rendered to the screen
    assert len(at.text) == 1
    assert at.text[0].value == "Success: Vinay is 25"

def test_validation_errors():
    """Test that invalid inputs trigger formatted Pydantic validation errors on screen."""
    at = AppTest.from_string(BASIC_APP_CODE)
    at.run()

    # 1. Fill out the form with INVALID data
    at.text_input[0].input("V").run()
    # Streamlit's UI will clamp this to the minimum allowed, so Pydantic will only complain about the name
    at.number_input[0].set_value(10).run() 

    # 2. Click the submit button
    at.button[0].click().run()

    # 3. Verify no success message was printed
    assert len(at.text) == 0

    # 4. Verify exactly ONE Streamlit error box popped up (for the Name field)
    assert len(at.error) == 1

    # 5. Verify our new, beautiful formatting is applied!
    error_message = at.error[0].value
    
    # Check for the bolded field name we added
    assert "**Name**:" in error_message
    
    # Check that the core Pydantic complaint is still there
    assert "at least 2 characters" in error_message.lower()



import os
from streamlit.testing.v1 import AppTest

def test_boolean_fields():
    """Test that boolean fields render as checkboxes and map correctly."""
    
    def boolean_app():
        import streamlit as st
        from pydantic import BaseModel
        # FIXED: We are importing from streamlit_autoform!
        from streamlit_autoform import autoform
        
        class UserPreferences(BaseModel):
            is_active: bool = False
            receive_newsletter: bool = True

        result = autoform(UserPreferences)
        if result:
            st.text(f"Active: {result.is_active}")
            st.text(f"Newsletter: {result.receive_newsletter}")

    from streamlit.testing.v1 import AppTest
    at = AppTest.from_function(boolean_app)
    at.run()

    # 1. Verify two checkboxes rendered on the screen
    assert len(at.checkbox) == 2

    # 2. Verify the Pydantic default values were respected in the UI
    assert at.checkbox[0].value == False
    assert at.checkbox[1].value == True

    # 3. Simulate a user interacting with the checkboxes
    at.checkbox[0].check().run()
    at.checkbox[1].uncheck().run()

    # 4. Click Submit
    at.button[0].click().run()

    # 5. Verify no errors popped up
    assert len(at.error) == 0

    # 6. Verify the form spit out the correct toggled data
    texts = [t.value for t in at.text]
    assert "Active: True" in texts
    assert "Newsletter: False" in texts