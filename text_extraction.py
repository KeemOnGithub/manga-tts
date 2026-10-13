import cv2 as cv
import sys
import easyocr
import matplotlib.pyplot as plt
    
img = cv.imread("./img/03.webp")

reader = easyocr.Reader(['en'])
result = reader.readtext(img)

for t in result:
    # print(t)
    bbox, text, score = t

    cv.rectangle(img, (int(bbox[0][0]), int(bbox[0][1])), (int(bbox[2][0]), int(bbox[2][1])), (0,255,0), 2)

plt.imshow(img)
plt.show()

# Sort by x-coordinate (right to left), then by y-coordinate (top to bottom)
sorted_results = sorted(result, key=lambda t: (-t[0][0][0], t[0][0][1]))

for t in sorted_results:
    bbox, text, score = t
    print(f"{text} (confidence: {score:.2f})")