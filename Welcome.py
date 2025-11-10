"""This is the app's splash page."""
import streamlit as st
import streamlit.components.v1 as components




st.set_page_config(layout="wide")
st.markdown("""
<style>
/* Enlarge labels for all main input types */
div[data-baseweb="input"] > div > div:first-child,
div[data-baseweb="textarea"] > div > div:first-child,
div[data-baseweb="numberinput"] > div > div:first-child,
div[data-baseweb="select"] > div:first-child,
div[data-baseweb="slider"] > div:first-child,
div[data-baseweb="radio"] > div:first-child {
    font-size: 18px !important;
    font-weight: 600 !important;
    color: #111 !important;
}
</style>
""", unsafe_allow_html=True)

def main():
    """
    This main function acts as the splash page for the app. Will be made more dynamic in future versions of the app with guides for usage.
    """

    st.title("Welcome to the Class Tracking and Report Generation Platform.")

    st.header("Quick Tips")

    text_boxes = [("Administrator Instructions", "If you are an <b>administrator</b>, please visit the page labeled <b>Admin Page</b> to initialize your organization's data, if your organization hasn't used the app before, to generate class assignments for a new semester, change report templates, and assign codes to denote different classes for the app's internal use."),
                  ("Instructor Instructions", "If you are an <b>instructor</b>, please visit the page labeled <b>Instructor Page</b> to generate student reports, log lessons, and view student data.")]


    #using default text from the Google API that Streamlit uses as a style sheet
    html_box_formatting = """
    <link href="https://fonts.googleapis.com/css2?family=Source+Sans+Pro:wght@400;600&display=swap" rel="stylesheet">
    <style>
    body {
        font-family: 'Source Sans Pro', sans-serif;
    }

    .box-container {
        display: flex;
        gap: 250px;
        justify-content: center;
        flex-wrap: wrap;
        margin-top: 30px;
    }

    /* Base box style */
    .text-box {
        background-color: #65CCFC;
        border: 20px solid #658BFC;
        border-bottom: 20px solid #658BFC;
        border-radius: 18px;
        padding: 20px;
        width: clamp(280px, 80vw, 800px);
        box-shadow: 50px 50px 50px rgba(101, 204, 252, 0.5);
        font-family: 'Source Sans Pro', sans-serif;
        word-wrap: break-word;
        opacity: 0;              /* start invisible */
        transform: translateY(40px); /* start slightly below */
        animation: slideIn 1s ease-out forwards;
    }

    /* Delay the second box slightly */
    .text-box:nth-child(2) {
        animation-delay: 0.3s;
    }

    /* Animation keyframes */
    @keyframes slideIn {
        from {
            opacity: 0;
            transform: translateY(40px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    .text-box h3 {
        margin-top: 0;
        margin-bottom: 12px;
        font-size: 80px;
        color: #2c3e50;
        text-align: center;
    }
    .text-box p {
        font-size: 50px;
        color: #333;
        line-height: 1.4;
        text-align: justify;
    }
    </style>

    <div class="box-container">
    """


    for title, text in text_boxes:
        html_box_formatting += f"""
        <div class="text-box">
            <h3>{title}</h3>
            <p>{text}</p>
        </div>
        """
    html_box_formatting += "</div>"

    # Render full HTML with components.html for reliable behavior
    components.html(html_box_formatting, height=1500, scrolling = True)  # increase height if text longer


if __name__ == "__main__":
    main()