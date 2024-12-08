import streamlit as st
import pdf2image
from io import BytesIO
import cv2
import numpy as np
from PIL import Image


pdf_uploaded = st.file_uploader("Select a file", type="pdf")
button = st.button("Upload")



if button and pdf_uploaded is not None:
    if pdf_uploaded.type == "application/pdf":
        images = pdf2image.convert_from_bytes(pdf_uploaded.read())
        
        min_contour_area = st.sidebar.slider("Contour Area",36000,50000)

        for i, page in enumerate(images):
            
            PDFimage = np.array(page)

            #image processing
            image = cv2.cvtColor(PDFimage, cv2.COLOR_BGR2GRAY)
            thresh = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
            opening_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3,3))
            kernel = np.ones((5,5),np.uint8)
            erode = cv2.erode(image, kernel, iterations=9)
            eroded_colored = cv2.cvtColor(erode, cv2.COLOR_GRAY2BGR)

            cnts , hierarchy = cv2.findContours(erode, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
            cnt = cnts[0]
            cv2.drawContours(image, cnts, -1, (0,255,255), 1)
            significant_contours = [cnt for cnt in cnts if cv2.contourArea(cnt) > min_contour_area]
            
            for i, contour in enumerate(cnts):
                if cv2.contourArea(contour) > min_contour_area:
                    # Get bounding rectangle
                    x, y, w, h = cv2.boundingRect(contour)

                    # Draw rectangle
                    cv2.rectangle(image, (0, y), (x + 5000, y + h), (0, 255, 0), 3)
                    cropped_img = image[y:y+h, 0:x+2000]
                    # cv2.imwrite(f"Cropped Image{i}.jpg", cropped_img)
                    significant_contours.append(contour)

            st.image(image, use_container_width=True)
        
        # st.sidebar.title(f"Number of significant contours: {len(significant_contours)}")
        
        img = page
        buf = BytesIO()

            # download image
            # img.save(buf, format="JPEG")
            # byte_im = buf.getvalue()
            # st.download_button("Download", data=byte_im, file_name=f"Image_{i}.png")