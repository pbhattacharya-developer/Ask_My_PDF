import os
import re
import PyPDF2
import streamlit as st
import google.generativeai as genai

from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

model = genai.GenerativeModel("gemini-1.5-flash")

# Initialize session state
if "pdf_text" not in st.session_state:
    st.session_state.pdf_text = ""
if "pdf_chunks" not in st.session_state:
    st.session_state.pdf_chunks = []
if "pdf_filename" not in st.session_state:
    st.session_state.pdf_filename = ""
if "messages" not in st.session_state:
    st.session_state.messages = []
if "chat_active" not in st.session_state:
    st.session_state.chat_active = False

def reset_session():
    st.session_state.pdf_text = ""
    st.session_state.pdf_chunks = []
    st.session_state.pdf_filename = ""
    st.session_state.messages = []
    st.session_state.chat_active = False
    st.rerun()

def clean_text(text):
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    return text

def chunk_text(text, chunk_size, chunk_overlap):
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        start += chunk_size - chunk_overlap
    return chunks

st.title("Ask My PDF")

uploaded_file = st.file_uploader("Upload a PDF file", type="pdf")

# Check if the file has been cleared
if uploaded_file is None and st.session_state.pdf_filename != "":
    reset_session()
    st.info("PDF removed. Session reset.")

if uploaded_file is not None:
    try:
        st.session_state.pdf_filename = uploaded_file.name
        reader = PyPDF2.PdfReader(uploaded_file)
        st.session_state.pdf_text = ""
        for page in reader.pages:
            st.session_state.pdf_text += page.extract_text()

        st.session_state.pdf_chunks = chunk_text(st.session_state.pdf_text, 1000, 0)

        cleaned_chunks = []
        for chunk in st.session_state.pdf_chunks:
            cleaned_chunk = clean_text(chunk)
            cleaned_chunks.append(cleaned_chunk)

        st.session_state.pdf_chunks = cleaned_chunks

        st.success("PDF uploaded successfully!")
        st.session_state.chat_active = True
    except Exception as e:
        st.error(f"Error uploading PDF: {e}")
        st.session_state.chat_active = False

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if st.session_state.chat_active:
    if prompt := st.chat_input("Ask any question to the PDF"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        if not st.session_state.pdf_chunks:
            st.session_state.messages.append({"role": "assistant", "content": "No PDF uploaded or processed. Please upload a PDF first."})
            with st.chat_message("assistant"):
                st.markdown("No PDF uploaded. Please upload a PDF first.")
        else:
            keywords = prompt.lower().split()
            relevant_chunks = []
            for chunk in st.session_state.pdf_chunks:
                for keyword in keywords:
                    if keyword in chunk.lower():
                        relevant_chunks.append(chunk)
                        break

            if not relevant_chunks:
                for chunk in st.session_state.pdf_chunks:
                    if prompt.lower() in chunk.lower():
                        relevant_chunks.append(chunk)

            context = "\n".join(relevant_chunks)
            gemini_prompt = f"Context: {context}\nQuestion: {prompt}"

            try:
                response = model.generate_content(gemini_prompt)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
                with st.chat_message("assistant"):
                    st.markdown(response.text)
            except Exception as e:
                st.error(f"Error querying Gemini: {e}")
else:
    if st.session_state.pdf_filename:
        st.info("Upload a new PDF to start")
    else:
        st.info("Upload a PDF to start the chat.")