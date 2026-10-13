from transformers import Qwen3VLForConditionalGeneration, AutoProcessor

def do_ocr_on_image(image_b64):
    # default: Load the model on the available device(s)
    model = Qwen3VLForConditionalGeneration.from_pretrained(
        "Qwen/Qwen3-VL-2B-Instruct", dtype="auto", device_map="auto"
    )

    processor = AutoProcessor.from_pretrained("Qwen/Qwen3-VL-2B-Instruct")

    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "image": image_b64,
                },
                {  
                     "type": "text", 
                     "text": """
                     Extract text from this image using OCR. Follow these requirements:
                        - Only include text found within speech bubbles. Any other text should not be included.
                        - Read from the right side of the image to the left side of the image, and from the top to the bottom.
                        - Output each bubble as a list item separated by newline 
                        - Maintain the reading order (first bubble read = #1, second = #2, etc.)
                        - Provide only the extracted text with no analysis or description
                    """
                },
            ],
        }
    ]

    # Preparation for inference
    inputs = processor.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=True,
        return_dict=True,
        return_tensors="pt"
    )
    inputs = inputs.to(model.device)

    # Inference: Generation of the output
    generated_ids = model.generate(**inputs, max_new_tokens=128)
    generated_ids_trimmed = [
        out_ids[len(in_ids) :] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
    ]
    output_text = processor.batch_decode(
        generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
    )
    print(output_text)
    return output_text
