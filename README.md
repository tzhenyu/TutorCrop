## Tutorial PDF Cropper
## Access here!!1
https://tutorial-pdf-cropper.streamlit.app/

I was annoyed by the university's tutorial file that lists questions without the gap below it. It is difficult for me to write answer beside the question. So I was thinking "it would be nice if I can write the answer to each question below so I can reference it better in the future".

This repo uses OpenCV to recognize the question block, crop it, create a gap below each question block, and create a new PDF file (so you can import to other apps and write answer on it easily).
This repo integrates with streamlit platform for easier use.

### How to use
![Video](https://s7.gifyu.com/images/SJcdD.gif)
There are 3 sliders you can control:
- Detection width: Draw the blue colored contour line around text and figure. It adjusts the width
- Crop Area: Crop detection area, there will be a green line, which will be cropped. You can adjust this slider to adjust which part to crop.
- Vertical Gap: Adjusts the gap between each questions

After adjusting it, click "Crop image" and it will generate a PDF! 

Before and after
<p float="left">
  <img src="https://s13.gifyu.com/images/SJcnR.jpg" width="800" />
  <img src="https://s13.gifyu.com/images/SJcn8.jpg" width="500" /> 
</p>
