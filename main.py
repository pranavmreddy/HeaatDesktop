import numpy
import cv2
import colour
import serial

from picamera.array import PiRGBArray
from picamera import PiCamera
import time
from fractions import Fraction

from pid import PID

# Camera setup
cam = PiCamera(resolution=(1920, 880), framerate=60)

cap = PiRGBArray(cam, size=(1920, 880))

# Serial setup
esp32 = serial.Serial("/dev/ttyUSB0", 115200, serial.EIGHTBITS, serial.PARITY_NONE, serial.STOPBITS_ONE)
esp32.write(b'            ')
time.sleep(2)
print("Pairing successful")
esp32.write(bytearray([44, 16, 32, 32, 32, 32, 32, 32, 32, 32, 32, 32]))
prev_time = time.time()

rgb_mode = False  # False is Kelvin mode, True is RGB mode
change_mode = False  # boolean that conveys whether or not to change the mode

red = 0
green = 0
blue = 0

brightness = 16

# Set white balance manually
cam.awb_mode = 'off'
cam.awb_gains = (Fraction(357, 256), Fraction(173, 128))


# Set initial target/output values
target = 6500
output = 6500

# Create PID control structure
pid = PID(0.5, 0, 0, target)


def update_target(x):
    global target, pid
    target = x + 2000
    pid.changeSetpoint(target)


def update_red(x):
    global red
    red = x


def update_green(x):
    global green
    green = x


def update_blue(x):
    global blue
    blue = x


def update_mode(x):
    global rgb_mode, change_mode, red, green, blue
    if x == 0:
        rgb_mode = False
    else:
        rgb_mode = True
        
    change_mode = True


def update_brightness(x):
    global brightness
    brightness = x


def calculate_input_temp(frame) -> float:
    array_RGB = numpy.array(list(cv2.mean(frame)[0:3][::-1]))

    array_tristimulus = colour.sRGB_to_XYZ(array_RGB / 255)

    array_chromaticity = colour.XYZ_to_xy(array_tristimulus)

    temporary = colour.xy_to_CCT(array_chromaticity, 'hernandez1999')

    if temporary < 1000:
        # print('Warm bound')
        return 1000
    elif temporary > 12000:
        # print('Cold bound')
        return 12000
    return temporary


def write_data(ser, value, rgb):
    global red, green, blue
    # print("New", "rgb" if rgb else "Kelvin", "Value:", value)
    if rgb:
        data_arr = bytearray([39, red, green, blue, 0, 100, 32, 32, 32, 32, 32, 32])
    else:
        data_arr = bytearray([37, (value >> 8) & 0xFF, value & 0xFF, 0, 100, 32, 32, 32, 32, 32, 32, 32])
    ser.write(data_arr)
    

# initial window setup
cv2.namedWindow('Heaat', flags=cv2.WINDOW_NORMAL)
cv2.resizeWindow('Heaat', 1920, 1010)

# Create a trackbars
cv2.createTrackbar('Mode- Left: Kelvin | Right: RGB', 'Heaat', 0, 1, update_mode)
cv2.createTrackbar('Preferred Color Temperature -2000', 'Heaat', 4500, 9000, update_target)
cv2.createTrackbar('Brightness', 'Heaat', brightness, 20, update_brightness)


# Main control loop:

for frame in cam.capture_continuous(cap, format="bgr", use_video_port=True):

    cap.truncate(0)
    frame_array = frame.array
    input = calculate_input_temp(frame_array)

    # Uncomment to see RGB values of each frame
    # print('RGB mean of frame:', cv2.mean(frame_array)[0:3][::-1])
    
    if not rgb_mode:
        temp = int(pid.calcVal(input))
        if temp >= 0 and output < 15000:
            output += temp
        elif temp < 0 and output > 100:
            output += temp
    
    if time.time() - prev_time > 1/20:
        write_data(esp32, output, rgb_mode)
        esp32.write(bytearray([44, brightness, 32, 32, 32, 32, 32, 32, 32, 32, 32, 32]))
        prev_time = time.time()

    # Uncomment for awb gains
    # print(cam.awb_gains)

    if change_mode:
        change_mode = False
        cv2.destroyAllWindows()
        cv2.namedWindow('Heaat', flags=cv2.WINDOW_NORMAL)
        cv2.resizeWindow('Heaat', 1920, 1010)
        cv2.createTrackbar('Mode- Left: Kelvin | Right: RGB', 'Heaat', (0 if not rgb_mode else 1), 1, update_mode)
        if not rgb_mode:
            cv2.createTrackbar('Preferred Color Temperature -2000', 'Heaat', target - 2000, 9000, update_target)
        else:
            cv2.createTrackbar('Red', 'Heaat', red, 255, update_red)
            cv2.createTrackbar('Green', 'Heaat', green, 255, update_green)
            cv2.createTrackbar('Blue', 'Heaat', blue, 255, update_blue)
        cv2.createTrackbar('Brightness', 'Heaat', brightness, 20, update_brightness)

    cv2.putText(img=frame_array, text=('RGB Mode' if rgb_mode else 'Kelvin Mode'), org=(10, 20),
                fontFace=cv2.FONT_HERSHEY_DUPLEX, fontScale=0.75, color=(0, 0, 255), thickness=2)
            
    if not rgb_mode:
        cv2.putText(img=frame_array, text='Target Temp: '+str(target) + ' K', org=(10, 80),
                    fontFace=cv2.FONT_HERSHEY_DUPLEX, fontScale=0.75, color=(0, 0, 255), thickness=2)
        cv2.putText(img=frame_array, text='Current Temp: ' + str(int(input)) + ' K', org=(10, 50),
                    fontFace=cv2.FONT_HERSHEY_DUPLEX, fontScale=0.75, color=(0, 0, 255), thickness=2)
        cv2.putText(img=frame_array, text='Output Temp: ' + str(int(output)) + ' K', org=(10, 110),
                    fontFace=cv2.FONT_HERSHEY_DUPLEX, fontScale=0.75, color=(0, 0, 255), thickness=2)

    cv2.imshow('Heaat', frame_array)

    # press 'q' to end
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break


cv2.destroyAllWindows()
esp32.write(bytearray([69] * 12))
print("Heaat closed...")
