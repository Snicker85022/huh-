import cv2
urls = [
 'rtsp://192.168.2.117:554/stream0?username=admin&password=E10ADC3949BA59ABBE56E057F20F883E',
 'rtsp://192.168.2.117:554/stream1?username=admin&password=E10ADC3949BA59ABBE56E057F20F883E',
]
for u in urls:
    print('trying', u)
    cap = cv2.VideoCapture(u, cv2.CAP_FFMPEG)
    cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 8000)
    ok, frame = cap.read()
    print('  ok=', ok)
    if ok:
        print('  frame', frame.shape)
        cv2.imwrite('ptz_test.jpg', frame)
        break
    cap.release()
