# ai_connectors.py
import os
import google.generativeai as genai
import openai
import anthropic
from dotenv import load_dotenv

load_dotenv()

# Configure clients
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
openai.api_key = os.getenv("OPENAI_API_KEY")
anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

def call_gemini(prompt, model="gemini-1.5-flash"):
    print("--- Calling Orchestrator (Gemini) ---")
    try:
        gemini_model = genai.GenerativeModel(model)
        response = gemini_model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Gemini Error: {str(e)}"

def call_gpt(prompt, model="gpt-4o"):
    print("--- Delegating to Specialist (GPT) ---")
    try:
        response = openai.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"GPT Error: {str(e)}"

def call_claude(prompt, model="claude-3-5-sonnet-20241022"):
    print("--- Delegating to Specialist (Claude) ---")
    try:
        response = anthropic_client.messages.create(
            model=model,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    except Exception as e:
        return f"Claude Error: {str(e)}"
