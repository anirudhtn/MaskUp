import cv2
import numpy as np
from tensorflow import keras
from imutils import resize
from imutils.video import VideoStream


def detect_and_predict_mask(frame, faceNet, maskNet):
    # construct BLOB from frame dimensions
    (h, w) = frame.shape[:2]
    blob = cv2.dnn.blobFromImage(frame, 1.0, (224, 224), (104, 177, 123))

    # Obtain face detection
    faceNet.setInput(blob)
    detections = faceNet.forward()
    print(detections.shape)

    # List of Faces, Locations and their Predictions
    faces, locs, preds = [], [], []

    for i in range(0, detections.shape[2]):
        # Extract confidence scores
        confidence = detections[0, 0, i, 2]

        # Filter out weak detections by setting a threshold
        if confidence > 0.5:
            # Compute the (x, y)-coordinates of bounding box
            box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
            (startX, startY, endX, endY) = box.astype("int")

            # Ensure dimensions are valid
            (startX, startY) = (max(0, startX), max(0, startY))
            (endX, endY) = (min(w - 1, endX), min(h - 1, endY))

            # Extract ROI and preprocess it
            face = frame[startY:endY, startX:endX]
            face = cv2.cvtColor(face, cv2.COLOR_BGR2RGB)
            face = cv2.resize(face, (224, 224))
            face = keras.preprocessing.image.img_to_array(face)
            face = keras.applications.mobilenet_v2.preprocess_input(face)

            faces.append(face)
            locs.append((startX, startY, endX, endY))

    # Make predictions if atleast one face was detected
    if len(faces) > 0:
        faces = np.array(faces, dtype="float32")
        preds = maskNet.predict(faces, batch_size=32)

    return (locs, preds)


def main():
    # Load pre-exisiting serialized face detector model
    prototxt = r"face_detector\deploy.prototxt"
    weights = r"face_detector\res10_300x300_ssd_iter_140000.caffemodel"
    faceNet = cv2.dnn.readNet(prototxt, weights)

    # Load face mask detector
    maskNet = keras.models.load_model("mask_detector.model")

    # Initialize video stream
    print("[PROGRESS] Starting video stream...")
    vs = VideoStream(src=0).start()

    while True:
        frame = vs.read()
        frame = resize(frame, width=400)

        (locs, preds) = detect_and_predict_mask(frame, faceNet, maskNet)

        for (loc, pred) in zip(locs, preds):
            (startX, startY, endX, endY) = loc
            (mask, withoutMask) = pred

            # Label and color to draw bounding box
            label = "Mask" if mask > withoutMask else "No Mask"
            color = (0, 255, 0) if label == "Mask" else (0, 0, 255)

            label = "{}: {:.2f}%".format(label, max(mask, withoutMask) * 100)

            cv2.putText(
                frame,
                label,
                (startX, startY - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                color,
                2,
            )
            cv2.rectangle(frame, (startX, startY), (endX, endY), color, 2)

        cv2.imshow("Frame", frame)

        # To close video stream
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break

    cv2.destroyAllWindows()
    vs.stop()


if __name__ == "__main__":
    main()
