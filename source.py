import cv2
import numpy as np
from PIL import Image
import io
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.pagesizes import A4
import pdf2image
import streamlit as st
import time
def create_pdf_with_crops_in_memory(cropped_images, vertical_spacing=100):
    # Create an in-memory buffer
    pdf_buffer = io.BytesIO()
    
    # Create the PDF canvas in the buffer
    c = canvas.Canvas(pdf_buffer, pagesize=A4)
    
    # Page dimensions (A4 size in points)
    page_width, page_height = A4
    left_margin = 0
    max_image_width = page_width - 2 * left_margin  # Allow for margins

    # Start position from top of first page
    current_y = page_height - 50  # 50-point margin at the top
    
    for img in cropped_images:
        # Convert OpenCV image (BGR) to RGB for PIL
        rgb_image = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # Convert to PIL Image
        pil_image = Image.fromarray(rgb_image)
        
        # Convert to ReportLab format
        img_buffer = io.BytesIO()
        pil_image.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        reportlab_image = ImageReader(img_buffer)
        
        # Get original image dimensions
        img_width, img_height = reportlab_image.getSize()
        
        # Calculate the scale factor to fit the image within page width
        scale_factor = min(1, max_image_width / img_width)
        scaled_width = img_width * scale_factor
        scaled_height = img_height * scale_factor
        
        # Check if we need a new page
        if current_y - scaled_height < 50:  # Leave 50 points margin at bottom
            c.showPage()
            current_y = page_height - 50  # Reset to top of new page
        
        # Calculate image position
        image_y = current_y - scaled_height
        
        # Draw the image
        c.drawImage(reportlab_image,
                    left_margin,
                    image_y,
                    width=scaled_width,
                    height=scaled_height)
        
        # Move down by image height plus spacing
        current_y = image_y - vertical_spacing
    
    # Save the PDF to the buffer
    c.save()
    pdf_buffer.seek(0)  # Move to the beginning of the buffer
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
        cv2.rectangle(output_image, (0, y), (x + 5000, y + h), (0, 255, 0), 3)
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
    st.set_page_config(page_title="Tutorial PDF Cropper",layout="wide",initial_sidebar_state="expanded")

    warning = st.container()
    col1, col2 = st.columns(2)
    with col1:
        
        # Initialize session states
        if 'processed_pages' not in st.session_state:
            st.session_state.processed_pages = []
        if 'cropped_images' not in st.session_state:
            st.session_state.cropped_images = []
        
        # File uploader
        
        # Sliders for parameters
        st.sidebar.title("Tutorial PDF Cropper")
        st.sidebar.write("Made by [tzhenyu](https://github.com/tzhenyu)")
        pdf_uploaded = st.sidebar.file_uploader("a",type="pdf",label_visibility="hidden")

        st.sidebar.header("Set File Parameters")  

        min_contour_area = st.sidebar.slider("Contour Area", 0, 300000, 40000)
        erode_iterations = st.sidebar.slider("Erosion Iterations", 1, 15, 9)
        vertical_gap = st.sidebar.slider("Vertical Gap (points)", 50, 300, 150)
        
        crop_button = st.sidebar.button("3. Crop Images")
        
        if pdf_uploaded is not None:
            st.header("Preview")

            # Process PDF pages
            if 'current_pdf' not in st.session_state or st.session_state.current_pdf != pdf_uploaded.name:
                st.session_state.current_pdf = pdf_uploaded.name
                images = pdf2image.convert_from_bytes(pdf_uploaded.read())
                st.session_state.processed_pages = []
                st.session_state.cropped_images = []
                
                for page in images:
                    PDFimage = np.array(page)
                    image = cv2.cvtColor(PDFimage, cv2.COLOR_BGR2GRAY)
                    st.session_state.processed_pages.append(image)
            
            # Process and display each page
            all_cropped_images = []
            
            for idx, page_image in enumerate(st.session_state.processed_pages):
                colored_image = page_image.copy()
                colored_image = cv2.cvtColor(page_image, cv2.COLOR_GRAY2RGB)
                page_placeholder = st.empty()
                contours = process_image(page_image, erode_iterations)
                processed_image, _, cropped_images = contourImg(
                    colored_image, 
                    contours, 
                    min_contour_area
                )
                all_cropped_images.extend(cropped_images)
                page_placeholder.image(processed_image, use_container_width=True)
            
            # When crop button is clicked

    with col2:
        try:
            if crop_button:
                # Create PDF with cropped images in memory
                st.session_state.cropped_images = all_cropped_images
                pdf_buffer = create_pdf_with_crops_in_memory(all_cropped_images, vertical_gap)
                
                # Add a download button
                warning.success("Image Cropped Successfully!")
                warning.download_button(
                    label="Download PDF",
                    data=pdf_buffer,
                    file_name=f"Cropped {pdf_uploaded.name}",
                    mime="application/pdf"
                )
                
            if st.session_state.cropped_images:
                st.header("Cropped Image Preview")
                
                for img in st.session_state.cropped_images:
                    st.image(img, use_container_width=True)

        except(AttributeError,UnboundLocalError):
            warning.warning("You haven't add any file yet!")



if __name__ == '__main__':
    main()
