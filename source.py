import cv2
import numpy as np
from PIL import Image
import io
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.pagesizes import A4
import pdf2image
import streamlit as st
import uuid
from pdf2image import convert_from_bytes

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
    st.set_page_config(page_title="Tutorial PDF Cropper", layout="wide", initial_sidebar_state="expanded")

    # Remove whitespace from the top of the page and sidebar
    st.markdown("""
            <style>
                .stMainBlockContainer {
                        padding-top: 1.5rem;
                        padding-bottom: 0rem;
                        padding-left: 3rem;
                        padding-right: 3rem;
                    }
            </style>
            """, unsafe_allow_html=True)
            
    warning = st.container()
    col1, col2 = st.columns(2)
    with col1.container():

        # Initialize session states
        if 'processed_pages' not in st.session_state:
            st.session_state.processed_pages = []
        if 'cropped_images' not in st.session_state:
            st.session_state.cropped_images = []

        # File uploader
        st.sidebar.title("Tutorial PDF Cropper")
        st.sidebar.write("Made by [tzhenyu](https://github.com/tzhenyu)")
        pdf_uploaded = st.sidebar.file_uploader("Upload PDF", type="pdf", label_visibility="hidden")

        st.sidebar.header("Parameters")

        min_contour_area = st.sidebar.slider("Crop Area", 0, 300000, 40000)
        erode_iterations = st.sidebar.slider("Detection Width", 1, 15, 9)
        vertical_gap = st.sidebar.slider("Vertical Gap", 50, 300, 150)

        crop_button = st.sidebar.button("3. Crop Images")

        if pdf_uploaded is not None:
            st.header("Preview")
            # Allow the user to select pages


            # Process PDF pages
            if 'current_pdf' not in st.session_state or st.session_state.current_pdf != pdf_uploaded.name:
                st.session_state.current_pdf = pdf_uploaded.name
                images = convert_from_bytes(pdf_uploaded.read())
                st.session_state.all_pages = [np.array(page) for page in images]

                # Reset session states
                st.session_state.selected_pages = list(range(len(st.session_state.all_pages)))  # Select all pages by default
                st.session_state.processed_pages = []
                st.session_state.cropped_images = []
                st.session_state.page_to_cropped_images = {}


            num_pages = len(st.session_state.all_pages)
            page_options = list(range(1, num_pages + 1))  # Pages start from 1 for user clarity
            with st.container(height=100):
                selected_pages = st.multiselect("Select pages:", options=page_options, default=page_options)

            if selected_pages:
                with st.container(height=650):
                    st.session_state.selected_pages = [page - 1 for page in selected_pages]  # Convert to zero-based index

                    # Process selected pages
                    st.session_state.processed_pages = []
                    for page_index in st.session_state.selected_pages:
                        PDFimage = st.session_state.all_pages[page_index]
                        image = cv2.cvtColor(PDFimage, cv2.COLOR_BGR2GRAY)
                        st.session_state.processed_pages.append(image)

                        colored_image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
                        contours = process_image(image, erode_iterations)
                        processed_image, _, cropped_images = contourImg(
                            colored_image, 
                            contours, 
                            min_contour_area
                        )
                        st.session_state.page_to_cropped_images[page_index + 1] = cropped_images

                        st.image(processed_image, use_container_width=True)

                    # for i, page_image in enumerate(st.session_state.processed_pages):
                    #     colored_image = cv2.cvtColor(page_image, cv2.COLOR_GRAY2RGB)
                    #     contours = process_image(page_image, erode_iterations)
                    #     processed_image, _, cropped_images = contourImg(
                    #         colored_image, 
                    #         contours, 
                    #         min_contour_area
                    #     )
                    #     st.session_state.cropped_images.extend(cropped_images)

                    #     st.image(processed_image, use_container_width=True)




    with col2.container():
        try:
            if crop_button:
                # Create PDF with cropped images from selected pages
                selected_cropped_images = []
                for page_number in st.session_state.selected_pages:
                    if page_number + 1 in st.session_state.page_to_cropped_images:
                        selected_cropped_images.extend(st.session_state.page_to_cropped_images[page_number + 1])

                pdf_buffer = create_pdf_with_crops_in_memory(selected_cropped_images, vertical_gap)

                # Add a download button


            # if st.session_state.page_to_cropped_images:
                st.header("Cropped Image Preview")
                with st.container(height=100):
                    st.download_button(
                        label="Download PDF",
                        data=pdf_buffer,
                        file_name=f"Cropped {pdf_uploaded.name}",
                        mime="application/pdf"
                    )

                with st.container(height=650):
                    for page_number in st.session_state.selected_pages:

                            if page_number + 1 in st.session_state.page_to_cropped_images:
                                for img in st.session_state.page_to_cropped_images[page_number + 1]:
                                        with st.container(border=True):
                                            st.image(img, use_container_width=True)
                                            st.checkbox("image", value=True, key=uuid.uuid4())
        except (AttributeError, UnboundLocalError):
            warning.warning("You haven't added any file yet!")


if __name__ == '__main__':
    main()
