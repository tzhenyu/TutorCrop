import streamlit as st
import pdf2image
from io import BytesIO
import cv2
import numpy as np
from PIL import Image

def contourImg(image, contours, min_contour_area):
    output_image = image.copy()
    # Calculate maximum allowed contour area as 50% of image area
    max_contour_area = (image.shape[0] * image.shape[1]) * 0.5
    
    # Filter contours by area
    significant_contours = [
        contour for contour in contours 
        if min_contour_area < cv2.contourArea(contour) < max_contour_area
    ]
    
    # st.sidebar.title(f"Number of significant contours: {len(significant_contours)}")
    
    # Draw all contours for visualization
    cv2.drawContours(output_image, significant_contours, -1, (0,255,255), 1)
    
    cropped_images = []
    for contour in significant_contours:
        x, y, w, h = cv2.boundingRect(contour)
        # Draw rectangle on output image
        cv2.rectangle(output_image, (0, y), (x + 2000, y + h), (0, 255, 0), 3)
        # Crop only the rectangular region
        cropped_img = image[y:y+h, 0:x+2000]
        cropped_images.append(cropped_img)
    cropped_images.reverse()
    
    return output_image, significant_contours, cropped_images

def process_image(image, erode_iterations):
    kernel = np.ones((5,5), np.uint8)
    erode = cv2.erode(image, kernel, iterations=erode_iterations)
    cnts, hierarchy = cv2.findContours(erode, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    return cnts

def on_slider_change():
    st.session_state.slider_changed = True

def main():
    st.set_page_config(layout="wide")
    st.title("PDF Image Processor")
    col1, col2 = st.columns(2)

    with col1:
        
        # Initialize session states
        if 'processed_pages' not in st.session_state:
            st.session_state.processed_pages = []
        if 'slider_changed' not in st.session_state:
            st.session_state.slider_changed = False
        if 'cropped_images' not in st.session_state:
            st.session_state.cropped_images = []
        
        # Create a placeholder for the image
        image_placeholder = st.empty()
        
        # File uploader
        pdf_uploaded = st.file_uploader("Select a file", type="pdf")
        
        # Sliders and button in sidebar with callback
        min_contour_area = st.sidebar.slider(
            "Contour Area",
            36000, 300000, 40000,
            on_change=on_slider_change
        )
        
        erode_iterations = st.sidebar.slider(
            "Erosion Iterations",
            1, 20, 9,
            on_change=on_slider_change
        )
        
        crop_button = st.sidebar.button("Crop Images")
        
        # Process PDF when uploaded
        if pdf_uploaded is not None:
            if 'current_pdf' not in st.session_state or st.session_state.current_pdf != pdf_uploaded.name:
                st.session_state.current_pdf = pdf_uploaded.name
                images = pdf2image.convert_from_bytes(pdf_uploaded.read())
                st.session_state.processed_pages = []
                st.session_state.cropped_images = []  # Reset cropped images for new PDF
                
                for page in images:
                    PDFimage = np.array(page)
                    image = cv2.cvtColor(PDFimage, cv2.COLOR_BGR2GRAY)
                    st.session_state.processed_pages.append({
                        'image': image,
                    })
            
            # Process and display each page
            all_cropped_images = []
            for idx, page_data in enumerate(st.session_state.processed_pages):
                # Create a placeholder for each page
                page_placeholder = st.empty()
                
                # Process image with current erosion setting
                contours = process_image(page_data['image'], erode_iterations)
                
                # Process contours and display image
                processed_image, significant_contours, cropped_images = contourImg(
                    page_data['image'], 
                    contours, 
                    min_contour_area
                )
                all_cropped_images.extend(cropped_images)
                
                # Update the image in the placeholder
                page_placeholder.image(processed_image, use_container_width=True)
            
            # When crop button is clicked, save and display cropped images
            if crop_button:
                st.session_state.cropped_images = all_cropped_images
            
            # Display cropped images if they exist

        with col2:
            if st.session_state.cropped_images:
                st.header("Cropped Images")
                for idx, img in enumerate(st.session_state.cropped_images):
                    st.image(img, use_container_width=True)

if __name__ == '__main__':
    main()