import cv2
import numpy as np
import win32gui
import win32ui
import win32con

def list_windows():
    windows = []

    def enum_window_callback(hwnd, extra):
        if win32gui.IsWindowVisible(hwnd):
            window_text = win32gui.GetWindowText(hwnd)
            if window_text:  # Boş olmayan pencere isimlerini al
                windows.append((hwnd, window_text))

    win32gui.EnumWindows(enum_window_callback, None)
    return windows

def capture_window(hwnd):
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    width = right - left
    height = bottom - top

    hwndDC = win32gui.GetWindowDC(hwnd)
    mfcDC = win32ui.CreateDCFromHandle(hwndDC)
    saveDC = mfcDC.CreateCompatibleDC()
    saveBitMap = win32ui.CreateBitmap()
    saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
    saveDC.SelectObject(saveBitMap)
    saveDC.BitBlt((0, 0), (width, height), mfcDC, (0, 0), win32con.SRCCOPY)

    bmpinfo = saveBitMap.GetInfo()
    bmpstr = saveBitMap.GetBitmapBits(True)

    img = np.frombuffer(bmpstr, dtype='uint8')
    img = img.reshape((bmpinfo['bmHeight'], bmpinfo['bmWidth'], 4))
    img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

    win32gui.DeleteObject(saveBitMap.GetHandle())
    saveDC.DeleteDC()
    mfcDC.DeleteDC()
    win32gui.ReleaseDC(hwnd, hwndDC)

    return img

def apply_transformations(frame):
    frame = cv2.resize(frame, (320, 240))

    transformations = [
        ("Original", frame),
        ("Gray", cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)),
        ("HSV", cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)),
        ("Lab", cv2.cvtColor(frame, cv2.COLOR_BGR2Lab)),
        ("Edge", cv2.Canny(frame, 100, 200)),
        ("Sepia", apply_sepia(frame)),
        ("Invert", cv2.bitwise_not(frame)),
        ("Blur", cv2.GaussianBlur(frame, (15, 15), 0)),
        ("Emboss", apply_emboss(frame)),
        ("Cartoon", apply_cartoon(frame)),
        ("Histogram Equalization", apply_histogram_equalization(frame)),
        ("CLAHE", apply_clahe(frame)),
        ("Laplacian", cv2.Laplacian(frame, cv2.CV_64F)),
        ("Sobel X", cv2.Sobel(frame, cv2.CV_64F, 1, 0, ksize=3)),
        ("Sobel Y", cv2.Sobel(frame, cv2.CV_64F, 0, 1, ksize=3)),
    ]

    transformed_images = []
    for name, img in transformations:
        if len(img.shape) == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        transformed_images.append((name, img))

    return transformed_images

def apply_sepia(image):
    kernel = np.array([[0.272, 0.534, 0.131],
                       [0.349, 0.686, 0.168],
                       [0.393, 0.769, 0.189]])
    sepia = cv2.transform(image, kernel)
    return cv2.convertScaleAbs(sepia)

def apply_emboss(image):
    kernel = np.array([[0, -1, -1],
                       [1, 0, -1],
                       [1, 1, 0]])
    embossed = cv2.filter2D(image, -1, kernel)
    return cv2.convertScaleAbs(embossed)

def apply_cartoon(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.medianBlur(gray, 7)
    edges = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_MEAN_C, 
                                  cv2.THRESH_BINARY, 9, 2)
    color = cv2.bilateralFilter(image, 9, 300, 300)
    cartoon = cv2.bitwise_and(color, color, mask=edges)
    return cartoon

def apply_histogram_equalization(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    equalized = cv2.equalizeHist(gray)
    return cv2.cvtColor(equalized, cv2.COLOR_GRAY2BGR)

def apply_clahe(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    clahe_applied = clahe.apply(gray)
    return cv2.cvtColor(clahe_applied, cv2.COLOR_GRAY2BGR)

def create_collage(transformed_images, selected_index=None):
    rows, cols = 3, 5
    h, w = transformed_images[0][1].shape[:2]
    collage = np.zeros((h * rows, w * cols, 3), dtype=np.uint8)

    for idx, (name, img) in enumerate(transformed_images):
        if idx >= rows * cols:
            break
        r, c = divmod(idx, cols)
        start_y, start_x = r * h, c * w
        collage[start_y:start_y + h, start_x:start_x + w] = img

        label_position = (start_x + 10, start_y + 30)
        cv2.putText(collage, name, label_position, cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 4, cv2.LINE_AA)
        cv2.putText(collage, name, label_position, cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)

    if selected_index is not None:
        # Seçilen kareyi orijinal çözünürlükte büyüt
        selected_name, selected_img = transformed_images[selected_index]
        original_resolution_img = cv2.resize(selected_img, (640, 480), interpolation=cv2.INTER_LINEAR)  # Büyütme
        return original_resolution_img

    return collage

def main():
    windows = list_windows()
    print("Açık olan pencereler:")
    for idx, (hwnd, title) in enumerate(windows):
        print(f"{idx + 1}: {title}")

    selected_index = int(input("İşlemek istediğiniz pencerenin numarasını seçin: ")) - 1
    if selected_index < 0 or selected_index >= len(windows):
        print("Geçersiz seçim!")
        return

    selected_hwnd = windows[selected_index][0]
    print(f"Seçilen pencere: {windows[selected_index][1]}")

    focused_index = None
    while True:
        frame = capture_window(selected_hwnd)
        if frame is None:
            print("Pencere yakalanamadı!")
            break

        transformed_images = apply_transformations(frame)
        collage = create_collage(transformed_images, focused_index)

        cv2.imshow("Processed Window - Collage", collage)

        key = cv2.waitKey(1) & 0xFF  # Sadece en düşük 8 biti al
        if key == ord('q'):
            break
        elif key == ord('r'):  # 'r' tuşu ile kolaja geri dön
            focused_index = None
        elif key >= 49 and key < 49 + len(transformed_images):  # Bir kare seç
            focused_index = key - 49  # '1' tuşu için index 0'dan başlar

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
