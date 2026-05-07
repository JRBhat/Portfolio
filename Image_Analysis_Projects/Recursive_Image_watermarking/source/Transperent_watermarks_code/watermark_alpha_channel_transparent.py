from PIL import Image
import os 

def watermark_image_center(input_image_path, output_image_path, watermark_image_path, alpha):
    # open input and watermark images
    photo = Image.open(input_image_path)
    watermark = Image.open(watermark_image_path)
    # new_size = (400, 400)
    
    # get image dimensions
    photo_width, photo_height = photo.size
    watermark = watermark.resize((500, 500), Image.Resampling.LANCZOS)
    watermark_width, watermark_height = watermark.size
    # create a transparent layer to blend watermark with the image

    layer = Image.new('RGBA', photo.size, (0,0,0,0))

    # calculate watermark position
    # watermark_position = ((photo_width - watermark_width)//2, (photo_height - watermark_height)//2) # centre of image
    watermark_position = ((photo_width - watermark_width)//2, (photo_height - watermark_height)//2) # 

    # blend the watermark with the transparent layer
    layer.paste(watermark, watermark_position)

    # apply transparency to the watermark layer
    alpha_layer = layer.copy()
    alpha_layer.putalpha(int(alpha * 255))
    layer = Image.alpha_composite(photo.convert('RGBA'), alpha_layer)

    # save the watermarked image
    layer.convert(photo.mode).save(output_image_path)


def watermark_image_corners(input_image_path, output_image_path, watermark_image_path, alpha):
    # open input and watermark images
    photo = Image.open(input_image_path)
    watermark = Image.open(watermark_image_path)
    # new_size = (400, 400)
    
    # get image dimensions
    photo_width, photo_height = photo.size
    watermark = watermark.resize((100, 100), Image.Resampling.LANCZOS)
    watermark_width, watermark_height = watermark.size
    # create a transparent layer to blend watermark with the image

    layer = Image.new('RGBA', photo.size, (0,0,0,0))

    # calculate watermark position
    # watermark_position = ((photo_width - watermark_width)//2, (photo_height - watermark_height)//2) # centre of image
    watermark_position = (photo_width - watermark_width, photo_height - watermark_height) # 

    # blend the watermark with the transparent layer
    layer.paste(watermark, watermark_position)

    # apply transparency to the watermark layer
    alpha_layer = layer.copy()
    alpha_layer.putalpha(int(alpha * 255))
    layer = Image.alpha_composite(photo.convert('RGBA'), alpha_layer)

    # save the watermarked image
    layer.convert(photo.mode).save(output_image_path)

if __name__ == '__main__':
    
    img_inp_path = r"C:\path\to\input_images"
    img_output_path = os.path.join(img_inp_path, "watermarked_copyright")
    # for img in os.listdir(img_inp_path):
    if not os.path.exists(img_output_path):
        os.mkdir(img_output_path)

    for img in os.listdir(img_inp_path):

        watermark_image_center(os.path.join(img_inp_path, img), os.path.join(img_output_path, img.replace(".png", "_output.png")), r"C:\path\to\watermark_logo.png", 0.05)

    # watermark_image_corners(r"C:\path\to\sample_image.png",
    # r'C:\path\to\output_corner_images',
    # r"C:\path\to\watermark_logo.png", 0.3)


