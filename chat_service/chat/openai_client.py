from openai import OpenAI
import os

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

def ask_ai(user_message: str, system_context: str):
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_context},
            {"role": "user", "content": user_message},
        ],
        temperature=0.4,
    )
    return resp.choices[0].message.content
