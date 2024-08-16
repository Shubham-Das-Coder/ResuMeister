import streamlit as st
from PyPDF2 import PdfReader
from transformers import GPT2LMHeadModel, GPT2Tokenizer
import random
import re
import os

# Function to extract text from PDF
def extract_text_from_pdf(pdf_file):
    pdf_reader = PdfReader(pdf_file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text

# Define the directory of your fine-tuned model
fine_tuned_model_dir = r"../fine-tuned-gpt2"

# Verify that the path exists
if not os.path.isdir(fine_tuned_model_dir):
    raise ValueError(f"The directory {fine_tuned_model_dir} does not exist.")

# Initialize the tokenizer and model
tokenizer = GPT2Tokenizer.from_pretrained(fine_tuned_model_dir)
gpt2_model = GPT2LMHeadModel.from_pretrained(fine_tuned_model_dir)

def generate_follow_up_question(answer_text, resume_text, asked_questions, asked_topics):
    # Create a context snippet based on key details from the resume
    snippet = create_context_snippet(resume_text)
    
    prompt = f"Based on the following resume snippet and the answer given, generate a relevant and professional follow-up question. The question should be closely related to the user's response and should avoid being generic or irrelevant. Ensure to switch topics if the user has expressed frustration or requested a topic change.\nResume Snippet: {snippet}\nAnswer: {answer_text}\nPrevious Questions: {'; '.join(asked_questions)}\nAsked Topics: {'; '.join(asked_topics)}\nFollow-up Question:"
    inputs = tokenizer.encode(prompt, return_tensors="pt")
    
    # Generate follow-up question
    outputs = gpt2_model.generate(
        inputs,
        max_new_tokens=50,
        num_return_sequences=1,
        temperature=0.6,
        top_p=0.9,
        top_k=50,
        pad_token_id=tokenizer.eos_token_id,
        eos_token_id=tokenizer.eos_token_id,
        no_repeat_ngram_size=3
    )
    
    generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)

    # Extract the question from the prompt
    question_start = generated_text.find("Follow-up Question:") + len("Follow-up Question:")
    question = generated_text[question_start:].strip()

    # Use regex to capture only the first sentence after "Follow-up Question:"
    question = re.split(r'[?.!]', question)[0].strip() + '?'

    # Check if the question is too generic or irrelevant
    if "resume" in question.lower() or "job" in question.lower() or len(question.split()) < 4:
        question = generate_fallback_question(asked_questions, asked_topics)

    # If the generated question is similar to a previous one, return a fallback question
    if question in asked_questions:
        question = generate_fallback_question(asked_questions, asked_topics)

    return question if question else "Can you provide more details?"

def create_context_snippet(resume_text):
    # Extract key information using regex or other methods
    # For simplicity, let's extract some key phrases and skills
    keywords = re.findall(r'\b\w+\b', resume_text)
    snippet = " ".join(keywords[:200])  # Create a snippet with the first 200 words
    return snippet

def generate_fallback_question(asked_questions, asked_topics):
    fallback_questions = [
        "Can you tell me more about your experience",
        "What projects are you most proud of?",
        "How do you stay updated with the latest trends in your field?",
        "Can you describe a challenging problem you've solved?",
        "What are your career goals?",
        "What programming languages are you familiar with?",
        "Can you explain a recent project you worked on?",
        "How do you approach problem-solving in your projects?"
    ]
    
    # Define topics to ensure diversity
    topics = ["AI", "ML", "Deep Learning", "Computer Vision", "Data Science", "Python", "Java"]
    
    # Check if the fallback questions are related to any of the asked topics
    remaining_questions = [q for q in fallback_questions if q not in asked_questions]
    if remaining_questions:
        return random.choice(remaining_questions)
    else:
        # Select a new topic and generate a question from that topic
        new_topic = random.choice([t for t in topics if t not in asked_topics])
        return f"Can you describe your experience with {new_topic}?"

# Streamlit app
st.title("AI Interviewer")

# Upload the resume PDF
uploaded_file = st.file_uploader("Upload your resume in PDF format", type="pdf")

# Session state initialization
if "current_question" not in st.session_state:
    st.session_state.current_question = None
if "resume_text" not in st.session_state:
    st.session_state.resume_text = None
if "conversation" not in st.session_state:
    st.session_state.conversation = []
if "asked_questions" not in st.session_state:
    st.session_state.asked_questions = []
if "asked_topics" not in st.session_state:
    st.session_state.asked_topics = []
if "user_answer" not in st.session_state:
    st.session_state.user_answer = ""

# Define the initial set of questions
initial_questions = [
    "What are your technical skills?",
    "What is your educational background?",
    "Can you describe your work experience?",
    "What projects have you worked on?",
    "What certifications do you hold?"
]

# Extract resume text if a file is uploaded
if uploaded_file is not None and st.session_state.resume_text is None:
    st.session_state.resume_text = extract_text_from_pdf(uploaded_file)

# Randomly select an initial question
if st.session_state.resume_text:
    if st.session_state.current_question is None and not st.session_state.conversation:
        if initial_questions:
            st.session_state.current_question = random.choice(initial_questions)
            st.session_state.conversation.append({
                "question": st.session_state.current_question,
                "answer": ""
            })
            st.session_state.asked_questions.append(st.session_state.current_question)
            # Add a topic based on the initial question
            topic = "Technical Skills" if "skills" in st.session_state.current_question.lower() else "General"
            st.session_state.asked_topics.append(topic)

    # Display the current question
    if st.session_state.current_question:
        st.write(f"Interviewer: {st.session_state.current_question}")

        # Create a form to handle the interview questions
        with st.form(key='interview_form'):
            user_answer = st.text_input("Your Answer:", key="user_answer_input")
            submit_button = st.form_submit_button(label='Submit Answer')

            if submit_button:
                if user_answer:
                    # Save the user's answer to the conversation history
                    st.session_state.conversation[-1]["answer"] = user_answer

                    # Generate the next question based on the user's answer and resume text
                    follow_up_question = generate_follow_up_question(user_answer, st.session_state.resume_text, st.session_state.asked_questions, st.session_state.asked_topics)
                    st.session_state.current_question = follow_up_question
                    st.session_state.conversation.append({
                        "question": follow_up_question,
                        "answer": ""
                    })
                    st.session_state.asked_questions.append(follow_up_question)

                    # Add a topic based on the new question
                    new_topic = "Technical Skills" if "skills" in follow_up_question.lower() else "General"
                    if new_topic not in st.session_state.asked_topics:
                        st.session_state.asked_topics.append(new_topic)

                    # Clear the input box by re-running the script
                    st.rerun()

# Stop interview button
if st.button("Stop Interview"):
    st.write("Interview stopped. Thank you for participating!")
    st.stop()

# Display the conversation history
if st.session_state.conversation:
    st.write("Conversation History:")
    for i, qa_pair in enumerate(st.session_state.conversation):
        st.write(f"Q{i+1}: {qa_pair['question']}")
        if qa_pair['answer']:
            st.write(f"A{i+1}: {qa_pair['answer']}")
