import cv2
cap = cv2.VideoCapture(0)
print('isOpened', cap.isOpened())
if cap.isOpened():
    ok, frame = cap.read()
    print('read_ok', ok)
    if ok and frame is not None:
        print('frame_shape', frame.shape)
    cap.release()
else:
    print('no_camera')
