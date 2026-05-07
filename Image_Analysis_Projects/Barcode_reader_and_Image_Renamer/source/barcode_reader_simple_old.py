# Importing library 
import cv2 
from pyzbar.pyzbar import decode 
import numpy as np
import os

# Make one method to decode the barcode 
def BarcodeReader(path): 
	
    # read the image in numpy array using cv2 
    img = cv2.imread(path)
    # gray = cv2.cvtColor(img[500:4760, 500:2840], cv2.COLOR_BGR2GRAY)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # blurred = cv2.blur(gray, (5, 5))
	
    # lower_val = np.array([200,200,200])
    # upper_val = np.array([255,255,255])
    fn = path.split("\\")[-1]
    mask = cv2.inRange(gray, 170, 255)
    # cv2.imshow("Image", mask) 
    # cv2.waitKey(0)
    
    
    # new_img_name = path_to_image.split("\\")[-1].replace(".JPG", "_mask.JPG")
    # path = "\\".join(path_to_image.split("\\")[:-1])
    # cv2.imwrite(os.path.join(path, new_img_name), mask) 
    # Decode the barcode image 
    detectedBarcodes = decode(mask) 
	
	# If not detected then print the message 
    if not detectedBarcodes: 
        print("Barcode Not Detected or your barcode is blank/corrupted!") 
        return None
    else: 
        
		# Traverse through all the detected barcodes in image 
        for barcode in detectedBarcodes: 
            # Locate the barcode position in image 
            (x, y, w, h) = barcode.rect 
            
            # Put the rectangle in image using 
            # cv2 to highlight the barcode 
            cv2.rectangle(img, (x-10, y-10), 
                        (x + w+10, y + h+10), 
                        (255, 0, 0), 5) 
            cv2.imwrite(r"bin\\"+ fn + "_masked.png", mask)
            cv2.imwrite(r"bin\\"+ fn + "_detected.png", img)
            if barcode.data!="": 
                
            # Print the barcode data 
                print(barcode.data) 
                return barcode.data
                # print(barcode.type) 
                
    #Display the image 
    # cv2.imshow("Image", img) 
    # cv2.waitKey(0)

    
    # new_img_name = path_to_image.split("\\")[-1].replace(".JPG", "_detctd.JPG")
    # path = "\\".join(path_to_image.split("\\")[:-1])
    # cv2.imwrite(os.path.join(path, new_img_name), img) 
    # cv2.destroyAllWindows() 

if __name__ == "__main__": 
# Take the image from user 
	path_to_image = "data/sample_image.JPG"
	BarcodeReader(path_to_image) 
