import os
import boto3

images_bucket = os.environ['BUCKET_NAME']
directory_path = os.environ['DIRECTORY_NAME']

img_directory = os.listdir(directory_path)
s3 = boto3.client('s3')
try:
    for img in img_directory:
        predicted_img_path = f'{directory_path}/{img}'
        s3.upload_file(predicted_img_path, images_bucket, img)
except Exception as e:
    print(f"Error: {str(e)}")
print(f'successfully download all images in {directory_path}')