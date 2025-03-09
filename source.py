import cv2
import numpy as np
from PIL import Image
import io
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.pagesizes import A4
import streamlit as st
import uuid
from pdf2image import convert_from_bytes

def create_pdf_with_crops_in_memory(cropped_images, vertical_spacing=100):
    pdf_buffer = io.BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=A4)
    
    page_width, page_height = A4
    left_margin = 0
    max_image_width = page_width - 2 * left_margin
    bottom_margin = 150  # Minimum space needed at bottom
    
    current_y = page_height - 50  # Start position
    
    for img in cropped_images:
        rgb_image = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(rgb_image)
        
        img_buffer = io.BytesIO()
        pil_image.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        reportlab_image = ImageReader(img_buffer)
        
        img_width, img_height = reportlab_image.getSize()
        scale_factor = min(1, max_image_width / img_width)
        scaled_width = img_width * scale_factor
        scaled_height = img_height * scale_factor
        
        # Check if image plus bottom margin fits on current page
        if current_y - scaled_height - bottom_margin < 0:
            c.showPage()
            current_y = page_height - 50
        
        image_y = current_y - scaled_height
        c.drawImage(reportlab_image,
                   left_margin,
                   image_y,
                   width=scaled_width,
                   height=scaled_height)
        
        current_y = image_y - vertical_spacing
    
    c.save()
    pdf_buffer.seek(0)
    return pdf_buffer

def contourImg(image, contours, min_contour_area):
    output_image = image.copy()
    # Calculate maximum allowed contour area as 50% of image area
    max_contour_area = (image.shape[0] * image.shape[1]) * 0.5
    
    # Filter contours by area
    significant_contours = [
        contour for contour in contours 
        if min_contour_area < cv2.contourArea(contour) < max_contour_area
    ]

    # Draw contours for visualization
    cv2.drawContours(output_image, contours, -1, (0,255,255), 1)
    
    # Store cropped images
    cropped_images = []
    for contour in significant_contours:
        x, y, w, h = cv2.boundingRect(contour)
        # Draw rectangle on output image
        cv2.rectangle(output_image, (x+w, y), (x , y + h), (0, 255, 0), 3)
        # Crop the region
        cropped_img = image[y:y+h, 0:x+2000]
        cropped_images.append(cropped_img)
    
    # Reverse the order if needed
    cropped_images.reverse()
    
    return output_image, significant_contours, cropped_images

def process_image(image, erode_iterations):
    """Process image with erosion and find contours."""

    _,thresholded_image = cv2.threshold(image, 127, 255, cv2.THRESH_BINARY)


    kernel = np.ones((5,5), np.uint8)
    erode = cv2.erode(thresholded_image, kernel, iterations=erode_iterations)

    cnts, hierarchy = cv2.findContours(erode, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    return cnts



def main():
    st.set_page_config(layout="centered", page_title="TutorCrop")
    st.markdown("## TutorCrop")
    st.markdown("By [tzhenyu](https://github.com/tzhenyu)")

    file_uploader = st.file_uploader("Upload PDF", type="pdf", label_visibility="hidden")

    if file_uploader: 
        images = convert_from_bytes(file_uploader.read())
        all_pages = [np.array(page) for page in images]

        num_pages = len(all_pages) # show number of pages
        page_options = list(range(1, num_pages + 1))  # Pages start from 1 for user clarity
        page_to_cropped_images = {} # Reset cropped images

        selected_pages = st.multiselect("Select pages:", options=page_options, default=page_options)
        selected_pages = [page - 1 for page in selected_pages]  # Convert to zero-based index

        # crop_button = parameters.button("3. Crop Images")

        if selected_pages:

            tab1, tab2= st.tabs(["Parameter Preview", "Cropped Images Preview"])

            with tab1.container():
                st.warning("Make sure all green and blue lines are correctly fit into each question. You can adjust the slider to get the best result. After that, click the next tab to choose which cropped image you want to exclude.")

                col1, col2 = st.columns(2)
                with col1:
                    min_contour_area = st.slider("Detected Area (green)", 0, 300000, 40000)
                with col2:
                    erode_iterations = st.slider("Detected Width (blue)", 1, 20, 9)

                for page_index in selected_pages:
                    PDFimage = all_pages[page_index]
                    image = cv2.cvtColor(PDFimage, cv2.COLOR_BGR2GRAY)

                    colored_image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
                    contours = process_image(image, erode_iterations)
                    processed_image, _, cropped_images = contourImg(
                        colored_image, 
                        contours, 
                        min_contour_area
                    )
                    page_to_cropped_images[page_index + 1] = cropped_images
                    st.image(processed_image, use_container_width=True)

            # Create a list to store selected images
            selected_cropped_images = []

            
            with tab2.container():

                st.warning("You can choose which cropped image you dont want, just tick the checkbox. After that, you can download file as PDF below.")

                # Initialize session state for checkboxes if not exists
                if 'exclusions' not in st.session_state:
                    st.session_state.exclusions = {}

                # Display images and checkboxes
                for page_number in selected_pages:
                    if page_number + 1 in page_to_cropped_images:
                        for idx, img in enumerate(page_to_cropped_images[page_number + 1]):
                            unique_key = f"exclude_page_{page_number + 1}_img_{idx}"
                            col1, col2 = st.columns([4, 1])
                            with col1:
                                st.image(img, use_container_width=True)
                            with col2:
                                st.session_state.exclusions[unique_key] = st.checkbox(
                                    "Exclude",
                                    key=unique_key,
                                    value=st.session_state.exclusions.get(unique_key, False)
                                )

                # Process selections
                selected_cropped_images = []
                for page_number in selected_pages:
                    if page_number + 1 in page_to_cropped_images:
                        for idx, img in enumerate(page_to_cropped_images[page_number + 1]):
                            unique_key = f"exclude_page_{page_number + 1}_img_{idx}"
                            if not st.session_state.exclusions.get(unique_key, False):
                                selected_cropped_images.append(img)
                                
                pdf_buffer = create_pdf_with_crops_in_memory(selected_cropped_images, 150)

                st.download_button(
                    label="Download PDF",
                    data=pdf_buffer,
                    file_name=f"Cropped {file_uploader.name}",
                    mime="application/pdf"
                )



if __name__ == '__main__':
    main()
