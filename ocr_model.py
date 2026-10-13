from transformers import Qwen3VLForConditionalGeneration, AutoProcessor, AutoModelForImageTextToText
import os
import base64
from langchain.agents import create_agent
from langchain_mistralai.chat_models import ChatMistralAI
from langgraph.checkpoint.memory import InMemorySaver
from dotenv import load_dotenv

load_dotenv()

api_key = os.environ["MISTRAL_API_KEY"]
checkpointer = InMemorySaver()
config = {"configurable": {"thread_id": "1"}}

def do_ocr_on_image(image_b64):
    vlm = ChatMistralAI(
        model="mistral-large-latest", api_key=api_key
    )
    agent = create_agent(vlm, tools=[], checkpointer=checkpointer)
    chat_response = agent.invoke(
        {
            "messages": [
            {
                "role": "system",
                "content": """
                    You are analyzing a manga page to identify which character is speaking each dialogue line.

                    You will be given:
                    - An image of a manga page
                    - A memory of character names identified from previous pages (for context)

                    Your task:
                    1. Read all dialogue on the page
                    2. Recognize the characters on the page
                    3. Match each line of dialogue to the character speaking it
                    4. Use previous character context to help resolve ambiguous cases

                    Return your answer in the format:
                    "[Character Name]: [dialogue line]"

                    If a speaker cannot be identified, label them as "Unknown" (by gender and number ). E.g. "Unknown Girl 1, Unknown Boy 1, etc."
                """
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "image": image_b64,
                    }
                ]
            }
        ]
        },
        config
    )

    print(chat_response)
    return chat_response

if __name__ == "__main__":
    # Path to the test image
    image_path = os.path.join("img", "horimiya ch1", "01.png")
    
    if os.path.exists(image_path):
        print(f"Loading image: {image_path}")
        with open(image_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')
            # Create data URI format that the processor expects
            data_uri = f"data:image/jpeg;base64,{base64_image}"
            
            # Run OCR on the image
            print("Running OCR...")
            do_ocr_on_image(data_uri)
    else:
        print(f"Error: Image not found at {image_path}")
