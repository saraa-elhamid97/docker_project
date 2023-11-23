import time
from pathlib import Path
from flask import Flask, request
from detect import run
import uuid
import yaml
from loguru import logger
import os
import boto3
import pymongo

images_bucket = os.environ['BUCKET_NAME']

with open("data/coco128.yaml", "r") as stream:
    names = yaml.safe_load(stream)['names']

app = Flask(__name__)

@app.route('/predict', methods=['POST'])
def predict():
    # Generates a UUID for this current prediction HTTP request. This id can be used as a reference in logs to identify and track individual prediction requests.
    prediction_id = str(uuid.uuid4())

    # Receives a URL parameter representing the image to download from S3
    img_name = request.args.get('imgName')
    original_img_path = f"{img_name}"
    s3 = boto3.client('s3')
    try:
        logger.info(f'prediction: {prediction_id}. start processing')
        s3.download_file(images_bucket, img_name, original_img_path)
        logger.info(f'prediction: {prediction_id}/{original_img_path}. Download img completed')
    except Exception as e:
        logger.error(f"Failed to download {img_name}. Error: {str(e)}")
        return f'Server Error', 500


    # Predicts the objects in the image
    run(
        weights='yolov5s.pt',
        data='data/coco128.yaml',
        source=original_img_path,
        project='static/data',
        name=prediction_id,
        save_txt=True
    )

    logger.info(f'prediction: {prediction_id}/{original_img_path}. done')

    # This is the path for the predicted image with labels
    # The predicted image typically includes bounding boxes drawn around the detected objects, along with class labels and possibly confidence scores.

    predicted_img_path = Path(f'static/data/{prediction_id}/{original_img_path}')
    predicted_img = "predicted_" + img_name
    try:
        logger.info(f"Start uploading {predicted_img} to s3")
        s3.upload_file(predicted_img_path, images_bucket, predicted_img)
        logger.info(f"Successfully uploaded {predicted_img} to s3")
    except Exception as e:
        logger.error(f"Failed to upload {predicted_img}. Error: {str(e)}")
        return f'Server Error', 500


    # Parse prediction labels and create a summary
    pred_summary_path = Path(f'static/data/{prediction_id}/labels/{original_img_path.split(".")[0]}.txt')
    if pred_summary_path.exists():
        with open(pred_summary_path) as f:
            labels = f.read().splitlines()
            labels = [line.split(' ') for line in labels]
            labels = [{
                'class': names[int(l[0])],
                'cx': float(l[1]),
                'cy': float(l[2]),
                'width': float(l[3]),
                'height': float(l[4]),
            } for l in labels]

        logger.info(f'prediction: {prediction_id}/{original_img_path}. prediction summary:\n\n{labels}')
        prediction_summary = {
            'prediction_id': prediction_id,
            'original_img_path': original_img_path,
            'predicted_img_path': str(predicted_img_path),
            'labels': labels,
            'time': time.time()
        }

        replica_set_name = "myReplicaSet"
        hosts = ["mongo1:27017", "mongo2:27018", "mongo3:27019"]
        try:
            logger.info(f"Connecting to MongoDB ")
            client = pymongo.MongoClient(f"mongodb://{','.join(hosts)}/?replicaSet={replica_set_name}")
            logger.info("Successfully connected to MongoDB")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB. Error: {str(e)}")
            return f'Server Error', 500

        db = client["object_detection_db"]
        collection = db["predicted_objects"]

        try:
            collection.insert_one(prediction_summary)
            prediction_summary['_id'] = str(prediction_summary['_id'])
            logger.info(f'Successfully inserted prediction for {img_name}')
        except Exception as e:
            logger.error(f'Failed to insert prediction for {img_name} to MongoDB. Error: {str(e)}')
            return f'Server Error', 500
        return prediction_summary
    else:
        return f'prediction: {prediction_id}/{original_img_path}. prediction result not found', 404


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8081)
