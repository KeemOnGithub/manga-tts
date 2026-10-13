import os
import base64
from ocr_model import do_ocr_on_image

def main():
    # Create input directory if it doesn't exist
    os.makedirs('img', exist_ok=True)
    
    imgPath = 'img'
    transPath = 'translated'

    images  = load_images_from_folder(imgPath)
    print ('Processing images:')
    names = load_names_from_folder(imgPath)
    print ('Names: ' + str(names))

    i = 0

    for img in images:
        print ('Processing image: ' + names[i])
        do_ocr_on_image(img)
        ## run tts here?
        i += 1


def load_images_from_folder(folder):
    images = []

    for filename in os.listdir(folder):
        filepath = os.path.join(folder, filename)
        with open(filepath, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')
            # Create data URI format that the processor expects
            data_uri = f"data:image/jpeg;base64,{base64_image}"
            images.append(data_uri)

    return images


def load_names_from_folder(folder):
    names = []

    for filename in os.listdir(folder):
        if filename is not None:
            names.append(filename)
            print (filename)

    return names


if __name__ == "__main__":
    main()
