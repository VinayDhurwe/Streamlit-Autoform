import sys
import typing
import datetime
from enum import Enum
import streamlit as st
from pydantic import BaseModel, ValidationError
from pydantic_core import PydanticUndefined
from pydantic import ValidationError

try:
    from types import UnionType
except ImportError:
    UnionType = type(None) 

def unwrap_optional(annotation: typing.Any) -> typing.Tuple[bool, typing.Any]:
    origin = typing.get_origin(annotation)
    args = typing.get_args(annotation)
    if origin is typing.Union or origin is UnionType:
        non_none_args = [a for a in args if a is not type(None)]
        if len(non_none_args) == 1:
            return True, non_none_args[0]
    return False, annotation

def autoform(
    model: typing.Type[BaseModel], 
    form_key: str = "autoform",
    submit_label: str = "Submit",
    clear_on_submit: bool = False
) -> typing.Optional[BaseModel]:
    
    error_state_key = f"{form_key}_errors"
    if error_state_key not in st.session_state:
        st.session_state[error_state_key] = {}
        
    errors = st.session_state[error_state_key]
    
    with st.form(key=form_key, clear_on_submit=clear_on_submit):
        
        # EXTRACTED: The widget rendering logic is now an isolated helper
        def _render_field(field_name: str, field_info, current_path: tuple):
            field_path = current_path + (field_name,)
            key = f"{form_key}_{'_'.join(field_path)}"
            
            is_optional, annotation = unwrap_optional(field_info.annotation)
            origin = typing.get_origin(annotation)
            args = typing.get_args(annotation)
            
            title = field_info.title or field_name.replace('_', ' ').title()
            help_text = field_info.description or ""
            default_val = field_info.default if field_info.default is not PydanticUndefined else None
            value = None

            # NEW: Extract disabled and placeholder attributes
            is_disabled = False
            placeholder_text = ""
            if field_info.json_schema_extra and isinstance(field_info.json_schema_extra, dict):
                is_disabled = field_info.json_schema_extra.get("disabled", False)
                placeholder_text = field_info.json_schema_extra.get("placeholder", "")

            if origin is typing.Literal:
                options = list(args)
                idx = options.index(default_val) if default_val in options else 0
                if len(options) <= 3:
                    value = st.radio(title, options=options, index=idx, help=help_text, disabled=is_disabled, key=key)
                else:
                    value = st.selectbox(title, options=options, index=idx, help=help_text, disabled=is_disabled, key=key)
                    
            elif isinstance(annotation, type) and issubclass(annotation, Enum):
                options = list(annotation)
                idx = options.index(default_val) if default_val in options else 0
                format_func = lambda x: x.name.replace("_", " ").title()
                if len(options) <= 3:
                    value = st.radio(title, options=options, index=idx, format_func=format_func, help=help_text, disabled=is_disabled, key=key)
                else:
                    value = st.selectbox(title, options=options, index=idx, format_func=format_func, help=help_text, disabled=is_disabled, key=key)
            
            elif origin in (list, set, typing.List, typing.Set):
                inner_type = args[0] if args else None
                inner_origin = typing.get_origin(inner_type)
                inner_args = typing.get_args(inner_type)
                options = []
                format_func = str
                
                if inner_origin is typing.Literal:
                    options = list(inner_args)
                elif isinstance(inner_type, type) and issubclass(inner_type, Enum):
                    options = list(inner_type)
                    format_func = lambda x: x.name.replace("_", " ").title()
                    
                if options:
                    default_selections = default_val if default_val is not None else []
                    value = st.multiselect(title, options=options, default=default_selections, format_func=format_func, help=help_text, disabled=is_disabled, key=key)
                    if origin in (set, typing.Set) and value is not None:
                        value = set(value)
                else:
                    st.warning(f"Cannot render multiselect for {field_name}.")
                    
            elif isinstance(annotation, type) and issubclass(annotation, BaseModel):
                st.markdown(f"#### {title}")
                value = _render_model(annotation, field_path)
                st.markdown("---")
                
            elif annotation is bool:
                val = default_val if isinstance(default_val, bool) else False
                value = st.checkbox(title, value=val, help=help_text, disabled=is_disabled, key=key)
                
            elif annotation in (int, float):
                min_val, max_val = None, None
                for m_data in field_info.metadata:
                    if hasattr(m_data, 'ge'): min_val = m_data.ge
                    elif hasattr(m_data, 'gt'): min_val = m_data.gt
                    if hasattr(m_data, 'le'): max_val = m_data.le
                    elif hasattr(m_data, 'lt'): max_val = m_data.lt
                    
                if min_val is not None and max_val is not None:
                    val = default_val if default_val is not None else min_val
                    value = st.slider(title, min_value=annotation(min_val), max_value=annotation(max_val), value=annotation(val), help=help_text, disabled=is_disabled, key=key)
                else:
                    step = 1.0 if annotation is float else 1
                    val = default_val if default_val is not None else (None if is_optional else (0.0 if annotation is float else 0))
                    value = st.number_input(title, min_value=annotation(min_val) if min_val is not None else None, max_value=annotation(max_val) if max_val is not None else None, value=val, step=step, help=help_text, disabled=is_disabled, key=key)
                    
            elif annotation is str:
                is_textarea = False
                is_password = False
                if field_info.json_schema_extra and isinstance(field_info.json_schema_extra, dict):
                    is_textarea = field_info.json_schema_extra.get("textarea", False)
                    is_password = field_info.json_schema_extra.get("password", False)
                    
                val = default_val if default_val is not None else ""
                if is_textarea:
                    value = st.text_area(title, value=val, placeholder=placeholder_text, help=help_text, disabled=is_disabled, key=key)
                else:
                    widget_type = "password" if is_password else "default"
                    value = st.text_input(title, value=val, placeholder=placeholder_text, help=help_text, disabled=is_disabled, key=key, type=widget_type)
                if is_optional and value == "":
                    value = None
                    
            elif annotation is datetime.date:
                val = default_val if default_val is not None else datetime.date.today()
                value = st.date_input(title, value=val, help=help_text, disabled=is_disabled, key=key)
                
            elif annotation is datetime.time:
                val = default_val if default_val is not None else datetime.datetime.now().time()
                value = st.time_input(title, value=val, help=help_text, disabled=is_disabled, key=key)

            elif annotation is bytes:
                uploaded_file = st.file_uploader(title, help=help_text, disabled=is_disabled, key=key)
                value = uploaded_file.getvalue() if uploaded_file is not None else default_val

            else:
                st.warning(f"Unsupported type {annotation} for field {field_name}")
                
            if field_path in errors:
                st.error(errors[field_path])
                
            return value

        def _render_model(m: typing.Type[BaseModel], current_path: tuple) -> dict:
            data = {}
            rows = {}
            
            # Group fields by row identifier
            for field_name, field_info in m.model_fields.items():
                row_id = f"auto_{field_name}" # Default: field gets its own row
                if field_info.json_schema_extra and isinstance(field_info.json_schema_extra, dict):
                    row_id = field_info.json_schema_extra.get("row", row_id)
                    
                if row_id not in rows:
                    rows[row_id] = []
                rows[row_id].append((field_name, field_info))
                
            # Render grouped fields into columns
            for row_id, fields in rows.items():
                if len(fields) > 1:
                    cols = st.columns(len(fields))
                    for col, (field_name, field_info) in zip(cols, fields):
                        with col:
                            data[field_name] = _render_field(field_name, field_info, current_path)
                else:
                    field_name, field_info = fields[0]
                    data[field_name] = _render_field(field_name, field_info, current_path)
                    
            return data

        form_data = _render_model(model, ())
        submitted = st.form_submit_button(submit_label)
        
        if submitted:
            try:
                # Attempt to create the Pydantic model with the form data
                validated_data = model(**form_data)
                st.success("Form submitted successfully!")
                return validated_data
                
            except ValidationError as e:
                # Catch the error, extract the details, and print nicely
                for error in e.errors():
                    # error['loc'] contains the field name, error['msg'] contains the reason
                    field_name = error['loc'][0]
                    error_message = error['msg']
                    
                    st.error(f"**{field_name.capitalize()}**: {error_message}")
                
    return None