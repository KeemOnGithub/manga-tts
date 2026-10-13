from transformers import Qwen3VLForConditionalGeneration, AutoProcessor, AutoModelForImageTextToText

def do_ocr_on_image(image_b64):
    # default: Load the model on the available device(s)
    model = AutoModelForImageTextToText.from_pretrained("HuggingFaceTB/SmolVLM2-500M-Video-Instruct")

    processor = AutoProcessor.from_pretrained("HuggingFaceTB/SmolVLM2-500M-Video-Instruct")

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

    inputs = processor.apply_chat_template(
        messages,
        add_generation_prompt=True,
        tokenize=True,
        return_dict=True,
        return_tensors="pt",
    ).to(model.device)

    outputs = model.generate(**inputs, max_new_tokens=40)
    print(processor.decode(outputs[0][inputs["input_ids"].shape[-1]:]))
    return processor.decode(outputs[0][inputs["input_ids"].shape[-1]:])

    # # Preparation for inference
    # inputs = processor.apply_chat_template(
    #     messages,
    #     tokenize=True,
    #     add_generation_prompt=True,
    #     return_dict=True,
    #     return_tensors="pt"
    # )
    # inputs = inputs.to(model.device)

    # # Inference: Generation of the output
    # generated_ids = model.generate(**inputs, max_new_tokens=128)
    # generated_ids_trimmed = [
    #     out_ids[len(in_ids) :] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
    # ]
    # output_text = processor.batch_decode(
    #     generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
    # )
    # print(output_text)
    # return output_text
