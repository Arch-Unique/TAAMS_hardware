
import os
import time
import serial
import csv
import RPi.GPIO as GPIO
from pyfingerprint.pyfingerprint import *
from enum import Enum
from RPLCD import i2c

# Initialise the LCD
lcd = i2c.CharLCD('PCF8574', 0x27, port=1, charmap='A00',
                  cols=20, rows=4)


class PageType(Enum):
    MAIN_MENU = 1
    ENROLL_MENU = 2
    ENROLL_STUDENT = 3
    ENROLL_LECTURER = 4
    ATTENDANCE_MENU = 5


currentPage = 1

ser = serial.Serial(
    port='/dev/ttyUSB0',  # change this accordingly
    baudrate=9600,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    timeout=1
)

currentPage = PageType.MAIN_MENU

finger = PyFingerprint('/dev/ttyUSB1', 57600, 0xFFFFFFFF, 0x00000000)

# Initialize keypad
# Replace this with your specific keypad library and setup code
upButton = 11
downButton = 13
okButton = 15
cancelButton = 16


def initSetup():
    # Send AT commands to configure LoRa module
    ser.write("AT\r\n")
    response = ser.readline().strip().decode('utf-8')
    if "+AT: OK" in response:
        print("AT Test passed")
    else:
        print("AT Test failed")

    ser.write("AT+MODE=TEST\r\n")
    response = ser.readline().strip().decode('utf-8')
    if "+MODE: TEST" in response:
        print("Lora set to Test mode")
    else:
        print("Lora set to a different mode")

    ser.write("AT+TEST=RFCFG,865.4,SF7,125,12,15,14,ON,OFF,OFF\r\n")
    response = ser.readline().strip().decode('utf-8')
    if "+TEST: RFCFG" in response:
        print("LoRa module configured")
    else:
        print("Failed to configure LoRa module")

    print("Initializing SD card...")
    chipSelect = 8
    GPIO.setup(chipSelect, GPIO.OUT)

    try:
        os.makedirs("/TAAMS/studentID")
        os.makedirs("/TAAMS/lecturersID")
        os.makedirs("/TAAMS/IdEnrolled")
        os.makedirs("/TAAMS/_COURSES_")
    except:
        print("Directories already exist")

    if not os.path.isdir("/TAAMS"):
        print("SD card not found")
        displayaAt0("Memory not found")
        while True:
            pass
    else:
        print("SD card initialized")

    GPIO.setmode(GPIO.BCM)
    GPIO.setup(upButton, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(downButton, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(okButton, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(cancelButton, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    # Initialize fingerprint sensor
    try:

        if (finger.verifyPassword() == False):
            raise ValueError('The given fingerprint sensor password is wrong!')

    except Exception as e:
        displayaAt0("Finger Sensor")
        lcd.cursor_pos = (0, 1)
        lcd.write_string("not found")
        print("Did not find fingerprint sensor")
        while True:
            pass


def displayaAt0(msg):
    lcd.clear()
    lcd.cursor_pos = (0, 0)
    lcd.write_string(msg)


def getFingerprintEnroll(id):
    updateDisplay = True
    p = -1
    print("Waiting for valid finger to enroll")
    displayaAt0("Place index finger")

    try:
        print('Waiting for finger...')

        # Wait that finger is read
        while (finger.readImage() == False):
            pass
        print("Image taken")
        displayaAt0("Image taken")

        # Converts read image to characteristics and stores it in charbuffer 1
        finger.convertImage(FINGERPRINT_CHARBUFFER1)
        print("Image converted")
        displayaAt0("Image converted")

        # Checks if finger is already enrolled
        result = finger.searchTemplate()
        positionNumber = result[0]

        if (positionNumber >= 0):
            print('Template already exists at position #' + str(positionNumber))
            exit(0)

        print('Remove finger...')
        displayaAt0('Remove finger...')
        time.sleep(2)

        print('Waiting for same finger again...')
        displayaAt0('Place same finger again')

        # Wait that finger is read again
        while (finger.readImage() == False):
            pass

        print("Image taken")
        displayaAt0("Image taken")

        # Converts read image to characteristics and stores it in charbuffer 2
        finger.convertImage(FINGERPRINT_CHARBUFFER2)
        print("Image converted")
        displayaAt0("Image converted")

        # Compares the charbuffers
        if (finger.compareCharacteristics() == 0):
            raise Exception('Fingers do not match')

        # Creates a template
        finger.createTemplate()

        # Saves template at new position number
        finger.storeTemplate(id)
        print('Finger enrolled successfully!')
        print('New template position #' + str(positionNumber))
        return 15

    except Exception as e:
        print('Operation failed!')
        print('Exception message: ' + str(e))
        displayaAt0(str(e))


def getInfo(promLCDAdrr, promptInfo, promLCDDispAdrr):
    toReturn = ""  # holder for what is to be returned

    # Display prompt on LCD
    lcd.clear()
    lcd.cursor_pos = (promLCDAdrr[0], promLCDAdrr[1])
    lcd.write_string(promptInfo)

    toReturn = input(promptInfo)

    return toReturn


def enrollSomeone():
    # the code below will create a folder called studentID on the sdcard and then create a file named studentID.csv in it

    # these variables determine where a prompt is displayed on the LCD and where the characters you type will appear
    # namePromLCD determines the location of the prompt
    # dispPromLCD determines where what you are typing will be going
    namePromLCD = [0, 0]
    dispPromLCD = [0, 2]

    id = 0

    # these variables are to store what will be in the enrollment file
    ID = ''
    regNo = ''
    surname = ''
    firstName = ''
    level = ''
    # course = ''
    department = ''
    faculty = ''

    success = 0  # used to determine if fingerprint was captured correctly

    # This block of code will prompt the user to enter the information
    ID = getInfo(namePromLCD, "Enter Your ID: ", dispPromLCD)

    while not ID.isDigit() or int(ID) < 0 or int(ID) > 129:
        ID = getInfo(namePromLCD, "Invalid ID(0-129):", dispPromLCD)

    id = int(ID)

    # while isIdenrolled(id, "IdEnrolled"):
    #     ID = getInfo(namePromLCD, "ID Taken,try again", dispPromLCD)

    regNo = getInfo(namePromLCD, "Enter Reg No: ", dispPromLCD)
    surname = getInfo(namePromLCD, "Enter Surname: ", dispPromLCD)
    firstName = getInfo(namePromLCD, "Enter First Name: ", dispPromLCD)
    level = getInfo(namePromLCD, "Enter Level: ", dispPromLCD)
    # course = getInfo(namePromLCD, "Enter Your course: ", dispPromLCD)
    department = getInfo(namePromLCD, "Enter Department: ", dispPromLCD)
    faculty = getInfo(namePromLCD, "Enter Faculty: ", dispPromLCD)

    id = int(ID)  # converts the ID given to int
    # call the finger enroll function and it will return 15 if successful (15 was just randomly chosen)
    success = getFingerprintEnroll(id)

    while success != 15:
        displayaAt0("Error, try again")
        time.sleep(0.5)
        lcd.clear()
        id = int(ID)
        success = getFingerprintEnroll(id)
        # lcd.clear()
        # lcd.cursor_pos = (0, 0)
        # lcd.write_string("Error, try again")
        # return

    #
    # if isnan(id): # check if the ID the user typed is even a number
    #     lcd.clear()
    #     lcd.cursor_pos = (0, 0)
    #     lcd.write_string("Invalid ID") # alert the user of the bad id
    # else:
    #     # wait while the files is being created

    if success == 15:  # if enrollment was successful
        # os.makedirs("studentID", exist_ok=True) # make folder if it doesnt exist
        os.chdir("/TAAMS/studentID")  # go to this directory
        # open the file called studentID, create it if it doent exist
        with open("studentID.csv", "a") as csv_file:
            writer = csv.writer(csv_file)
            # write the data to the csv file
            writer.writerow([ID, regNo, surname, firstName,
                             level, department, faculty])
        displayaAt0("Reg. successful")
        print("Registration successful")
    else:
        print("Check Finger Scanner")

    time.sleep(2)


def getFingerprintIDez():
    updateDisplay = True
    # Converts read image to characteristics and stores it in charbuffer 1

    try:
        print('Waiting for finger...')
        displayaAt0("Place finger")

        # Wait that finger is read
        while (finger.readImage() == False):
            pass
        finger.convertImage(FINGERPRINT_CHARBUFFER1)

        # Searchs template
        result = finger.searchTemplate()

        positionNumber = result[0]
        accuracyScore = result[1]

        if (positionNumber == -1):
            print('No match found!')
            displayaAt0("ID not found")

        else:
            print('Found template at position #' + str(positionNumber))
            print('The accuracy score is: ' + str(accuracyScore))
            displayaAt0("ID found")
        return positionNumber

    except Exception as e:
        print('Operation failed!')
        print('Exception message: ' + str(e))
        return -1


def getIdDetails(id, file_name):
    file_name += ".csv"
    in_str = str(id)
    to_return = ""
    buffer_size = 200

    with open("/TAAMS/studentID/" + file_name, "r") as csv_file:
        csv_reader = csv.reader(csv_file)

        for row in csv_reader:
            buffer = row[0][:buffer_size]
            id_from_csv = buffer.split(",")[0]

            print(id_from_csv + ": comparing to: " + in_str)

            if id_from_csv == in_str:
                print("Id found")
                to_return = ",".join(row)
                break

    csv_file.close()

    if to_return:
        print("student detail to return is:")
        print(to_return)
        return to_return

    # return "0" if the ID is not found
    return "0"


def takeAttendance():
    # initialize variables
    name_prom_lcd = [0, 0]
    disp_prom_lcd = [0, 2]
    id = 0
    lecturer_id = getFingerprintIDez()
    id = ''
    regNo = ''
    surname = ''
    firstname = ''
    level = ''
    department = ''
    faculty = ''
    courseInSession = ''
    marked = [0] * 150
    markedCounter = 0

    # loop until a valid lecturer ID is obtained
    while (lecturer_id == -1 or lecturer_id < 129):
        if (lecturer_id == -1):
            displayaAt0("ID not found")
            time.sleep(1)
        elif (lecturer_id < 129 and lecturer_id != -1):
            displayaAt0("Student cannot")
            lcd.cursor_pos = (0, 1)
            lcd.write_string("authorize attendance")
            time.sleep(1)
        lecturer_id = getFingerprintIDez()

    # get lecturer courses and course in session
    lectute_and_courses = getLecturerCourses(
        lecturer_id, "/TAAMS/lecturersID", "lecturersID")
    courses_str = lectute_and_courses[0]
    num_of_courses = int(lectute_and_courses[1])
    print("The courses of this lecturer are: ", lectute_and_courses[0])

    print("The no of courses of this lecturer are: ", lectute_and_courses[1])
    courseInSession = returnCourseForAttendance(courses_str, num_of_courses)
    print("The course in session is ", courseInSession)

    # create course directory
    os.makedirs("/TAAMS/_COURSES_/" + courseInSession, exist_ok=True)

    # loop until attendance is ended
    while True:
        id = getFingerprintIDez()
        if (isMarked(id, marked)):
            displayaAt0("You marked Already")

        if id == -1:
            displayaAt0("ID not found")
            time.sleep(1)
            continue

        if id == lecturer_id:
            sendStudentDetailToLora("_", "_", "_", "_", "_", "_", "900")
            #sendStudentDetailToLora("surname", "firstname", "regNo", "courseInSession", "department", "faculty", "level")
            ser.write(b"Finished")
            displayaAt0("Attendnce Ended...")

            time.sleep(1)
            currentPage = PageType.MAIN_MENU
            break

        elif 0 <= id <= 129:
            #lcd_print("ID found please wait...")

            student_details = getIdDetails(id, "studentID")
            print("Gotten student details:", student_details)

            id, regNo, surname, firstname, level, department, faculty = student_details.split(
                ',')
            print("This is inside the take attendance function")
            print(id)
            print(regNo)
            print(firstname)
            print(level)
            print(faculty)

            courseDir = "/TAAMS/COURSES/" + courseInSession
            if not os.path.exists(courseDir):
                os.makedirs(courseDir)

            # this is the name of the file that will be created
            StudentFileName = surname + "_" + firstname
            print("This is the file name for the student")

            StudentFileName += ".csv"  # csv will be attached to the end of the file
            print(StudentFileName)

            try:
                with open(StudentFileName, 'w', newline='') as csvfile:
                    fieldnames = ['id', 'regNo', 'surname',
                                  'firstname', 'level', 'department', 'faculty']
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                    writer.writeheader()
                    writer.writerow({
                        'id': id,
                        'regNo': regNo,
                        'surname': surname,
                        'firstname': firstname,
                        'level': level,
                        'department': department,
                        'faculty': faculty
                    })
                marked[markedCounter] = id
                markedCounter += 1
                displayaAt0("Marked Successfully")
                lcd.cursor_pos = (0, 1)
                lcd.write_string(firstname)
                lcd.cursor_pos = (0, 2)
                lcd.write_string(surname)
                time.sleep(1)

                if sendStudentDetailToLora(surname, firstname, regNo, courseInSession, department, faculty, level):
                    displayaAt0("Attendance Sent!")
                    lcd.cursor_pos = (0, 1)
                    lcd.write_string("Succesfully")
                    time.sleep(1)
                else:
                    displayaAt0("Attendance not Sent!")

            except IOError:
                lcd.clear()
                lcd.cursor_pos = (0, 0)
                lcd.write_string("Failed to open file")


def enrollLecturer():
    # these variables determines where a prompt is displayed on the lcd and where the characters you type will appear
    # namePromLCD determines the location of the prompt
    # dispPromLCD determines where what you are typing will be going
    name_prom_lcd = [0, 0]
    disp_prom_lcd = [0, 2]

    # these variables are to store what will be in the enrollment file
    ID = ''
    id_int = 0
    staffID = ''
    surname = ''
    firstName = ''
    no_of_courses = ''
    updateDisplay = True
    courses = [None] * 5
    btnCancelWasDown = False
    okBtnWasDown = False
    loop_count = 1
    courseCount = 0
    success = 0  # used to determine if fingerprint was captured correctly
    # This block of code will prompt the user to enter the information
    ID = getInfo(name_prom_lcd, "Enter ID(130-149): ", disp_prom_lcd)
    while not isNumeric(ID) or int(ID) < 129 or int(ID) > 149:
        ID = getInfo(name_prom_lcd, "Invalid ID(141-162): ", disp_prom_lcd)

    id_int = int(ID)

    staffID = getInfo(name_prom_lcd, "Enter StaffID: ", disp_prom_lcd)
    surname = getInfo(name_prom_lcd, "Enter Surname: ", disp_prom_lcd)
    firstName = getInfo(name_prom_lcd, "Enter Firstname: ", disp_prom_lcd)
    no_of_courses = getInfo(name_prom_lcd, "No. of Courses: ", disp_prom_lcd)

    while not no_of_courses.isnumeric() or int(no_of_courses) < 0 or int(no_of_courses) > 3:
        no_of_courses = getInfo(
            name_prom_lcd, "Invalid, Enter(1-3):", disp_prom_lcd)

    print(int(no_of_courses))

    courses[courseCount] = getInfo(
        name_prom_lcd, "Enter Course " + str(loop_count) + ":", disp_prom_lcd)

    if int(no_of_courses) > 1:
        courseCount += 1
        while loop_count < int(no_of_courses):
            loop_count += 1
            courses[courseCount] = getInfo(
                name_prom_lcd, "Enter Course " + str(loop_count) + ":", disp_prom_lcd)
            courseCount += 1

    for i in range(int(no_of_courses)):
        print(courses[i])

    id_int = int(ID)
    # call the finger enroll function and it will return 15 if successful (15 was just randomly chosen)
    success = getFingerprintEnroll(id_int)
    while success != 15:
        displayaAt0("Error, try again")
        time.sleep(0.5)
        lcd.clear()
        id_int = int(ID)
        success = getFingerprintEnroll(id_int)
    if success == 15:  # if enrollment was successful
        if not os.path.exists('/TAAMS/lecturersID'):
            os.makedirs('/TAAMS/lecturersID')

        os.chdir('/TAAMS/lecturersID')

        with open('lecturersID.csv', mode='a') as csv_file:
            csv_writer = csv.writer(csv_file)
            csv_writer.writerow(
                [ID, no_of_courses, staffID, surname, firstName] + courses)

        displayaAt0("Registration")
        lcd.cursor_pos = (0, 1)
        lcd.write_string("Successful")
        print("Registration successful")

    else:
        print('Check Fingerprint Scanner')

    time.sleep(2)


def buttonIsDown(button):
    #GPIO.setup(button, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    readOne = GPIO.input(button)
    time.sleep(0.01)
    readTwo = GPIO.input(button)

    if readOne == GPIO.LOW and readTwo == GPIO.LOW:
        return True
    else:
        return False


def buttonIsUp(button):
    readOne = GPIO.input(button)
    time.sleep(0.01)
    readTwo = GPIO.input(button)

    if readOne == GPIO.HIGH and readTwo == GPIO.HIGH:
        return True
    else:
        return False


def getLecturerCourses(id, path, file_name):
    id_from_csv = ""

    in_str = str(id)
    file_name += ".csv"
    buffer_size = 200
    courses = []

    try:
        with open(path + "/" + file_name, "r") as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=",")
            for row in csv_reader:
                id_from_csv = row[0]
                if id_from_csv == in_str:
                    no_of_courses = int(row[1])
                    staff_id = row[2]
                    surname = row[3]
                    first_name = row[4]
                    for i in range(no_of_courses):
                        courses.append(row[i+5])
                    break
            else:
                print("ID not found")
                return None
    except FileNotFoundError:
        print("Failed to open file")
        return None

    courses_to_return = ",".join(courses)

    # return the data gotten
    to_return = [courses_to_return, str(no_of_courses)]
    print("The courses I will return are:", to_return[0])
    print("The number of courses I will return is:", to_return[1])
    return to_return


def returnCourseForAttendance(string_courses_to_return, no_of_courses):
    courses = [''] * 5
    char_courses_to_return = list(string_courses_to_return)

    for i in range(len(string_courses_to_return)):
        char_courses_to_return[i] = string_courses_to_return[i]

    # Split courses string and store in array
    courses[0] = strtok(char_courses_to_return, ",")
    print("The courses")
    print(courses[0])

    if int(no_of_courses) > 1:
        for i in range(1, int(no_of_courses)):
            courses[i] = strtok(None, ",")
            print(courses[i])

    courseCount = int(no_of_courses)
    print("no of courses:", courseCount)
    updateDisplay = True
    menuSelector = 0
    btnDownWasDown = False
    btnUpWasDown = False
    okBtnWasDown = False

    while True:
        if updateDisplay:
            print("no of courses:", courseCount)

            if courseCount == 1:
                print("I am in where number of courses is:", courseCount)
                printSelectedAt0(1, menuSelector + 1)
                lcd.cursor_pos = (1, 0)
                lcd.write_string(courses[0])

            if courseCount == 2:
                print("I am in where number of courses is:", courseCount)
                printSelectedAt0(1, menuSelector + 1)
                lcd.cursor_pos = (1, 0)
                lcd.write_string(courses[0])
                lcd.cursor_pos = (0, 1)
                printSelected(2, menuSelector + 1)
                lcd.cursor_pos = (1, 1)
                lcd.write_string(courses[1])

            if courseCount == 3:
                print("I am in where number of courses is:", courseCount)
                printSelectedAt0(1, menuSelector + 1)
                lcd.cursor_pos = (1, 0)
                lcd.write_string(courses[0])
                lcd.cursor_pos = (0, 1)
                printSelected(2, menuSelector + 1)
                lcd.cursor_pos = (1, 1)
                lcd.write_string(courses[1])
                lcd.cursor_pos = (0, 2)
                printSelected(3, menuSelector + 1)
                lcd.cursor_pos = (1, 2)
                lcd.write_string(courses[2])

            if courseCount == 4:
                print("I am in where number of courses is:", courseCount)
                printSelectedAt0(1, menuSelector + 1)
                lcd.cursor_pos = (1, 0)
                lcd.write_string(courses[0])
                lcd.cursor_pos = (0, 1)
                printSelected(2, menuSelector + 1)
                lcd.cursor_pos = (1, 1)
                lcd.write_string(courses[1])
                lcd.cursor_pos = (0, 2)
                printSelected(3, menuSelector + 1)
                lcd.cursor_pos = (1, 2)
                lcd.write_string(courses[2])
                lcd.cursor_pos = (0, 3)
                printSelected(4, menuSelector + 1)
                lcd.cursor_pos = (1, 3)
                lcd.write_string(courses[3])

            updateDisplay = False

        # Capture button states
        if buttonIsDown(downButton):
            btnDownWasDown = True

        if buttonIsDown(upButton):
            btnUpWasDown = True

        if buttonIsDown(okButton):
            okBtnWasDown = True

        if btnDownWasDown and buttonIsUp(downButton):
            menuSelector -= 1
            btnDownWasDown = False
            updateDisplay = True
        if btnUpWasDown and buttonIsUp(upButton):
            menuSelector += 1
            btnUpWasDown = False
            updateDisplay = True

        if okBtnWasDown and buttonIsUp(okButton):
            if menuSelector == 0:
                return courses[0]
            elif menuSelector == 1:
                return courses[1]
            elif menuSelector == 2:
                return courses[2]
            elif menuSelector == 3:
                return courses[3]

        if courseCount == 1:
            menuSelector = 0
        elif courseCount == 2:
            menuSelector = abs(menuSelector % 2)  # to reset the menu selector
        elif courseCount == 3:
            menuSelector = abs(menuSelector % 3)  # to reset the menu selector
        elif courseCount == 4:
            menuSelector = abs(menuSelector % 3)  # to reset the menu selector
        print(menuSelector)


def printSelected(pos1, pos2):
    if pos1 == pos2:
        lcd.write_string(">")
    else:
        lcd.write_string(" ")


def printSelectedAt0(pos1, pos2):
    if pos1 == pos2:
        displayaAt0(">")
    else:
        displayaAt0(" ")


def mainMenu():
    updateDisplay = True
    menuSelector = 0
    btnDownWasDown = False
    btnUpWasDown = False
    okBtnWasDown = False
    while True:
        if updateDisplay:
            printSelectedAt0(1, menuSelector + 1)
            lcd.cursor_pos = (1, 0)
            lcd.write_string("Enroll")
            lcd.cursor_pos = (0, 1)
            printSelected(2, menuSelector + 1)
            lcd.cursor_pos = (1, 1)
            lcd.write_string("Attendance")
            updateDisplay = False
        # end of update menu

        # capture button states
        if buttonIsDown(downButton):
            btnDownWasDown = True
        if buttonIsDown(upButton):
            btnUpWasDown = True
        if buttonIsDown(okButton):
            okBtnWasDown = True

        if btnDownWasDown and buttonIsUp(downButton):
            menuSelector -= 1
            btnDownWasDown = False
            updateDisplay = True
        if btnUpWasDown and buttonIsUp(upButton):
            menuSelector += 1
            btnUpWasDown = False
            updateDisplay = True

        if okBtnWasDown and buttonIsUp(okButton):
            if menuSelector == 0:
                currentPage = PageType.ENROLL_MENU
                return
            elif menuSelector == 1:
                currentPage = PageType.ATTENDANCE_MENU
                return

        menuSelector = abs(menuSelector % 2)  # to reset the menu selector

        print(menuSelector)


def enrollMenu():
    updateDisplay = True
    menuSelector = 0
    btnDownWasDown = False
    btnUpWasDown = False
    okBtnWasDown = False
    cancelBtnWasDown = False
    while True:
        if updateDisplay:
            printSelectedAt0(1, menuSelector + 1)
            lcd.cursor_pos = (1, 0)
            lcd.write_string("Enroll student")
            lcd.cursor_pos = (0, 1)
            printSelected(2, menuSelector + 1)
            lcd.cursor_pos = (1, 1)
            lcd.write_string("Enroll lecturer")
            updateDisplay = False
        # end of update menu

        # capture button states
        if buttonIsDown(downButton):
            btnDownWasDown = True
        if buttonIsDown(upButton):
            btnUpWasDown = True
        if buttonIsDown(okButton):
            okBtnWasDown = True
        if buttonIsDown(cancelButton):
            cancelBtnWasDown = True

        if btnDownWasDown and buttonIsUp(downButton):
            menuSelector -= 1
            btnDownWasDown = False
            updateDisplay = True
        if cancelBtnWasDown and buttonIsUp(cancelButton):
            currentPage = PageType.MAIN_MENU
            cancelBtnWasDown = False
            updateDisplay = True
            return
        if btnUpWasDown and buttonIsUp(upButton):
            menuSelector += 1
            btnUpWasDown = False
            updateDisplay = True

        if okBtnWasDown and buttonIsUp(okButton):
            if menuSelector == 0:
                currentPage = PageType.ENROLL_STUDENT
                return
            elif menuSelector == 1:
                currentPage = PageType.ENROLL_LECTURER
                return

        menuSelector = abs(menuSelector % 2)  # to reset the menu selector

        print(menuSelector)


def attendanceMenu():
    takeAttendance()
    #  lcd.cursor_pos = (0, 0);
    #  lcd.write_string("Press OK to start");
    # do the actual attendance


def enrollTheLecturer():
    enrollLecturer()


def enrollStudent():
    enrollSomeone()


def sendStudentDetailToLora(surname, firstname, regNo, courseInSession, department, faculty, level):
    to_send = 'AT+TEST=TXLRSTR, "{}","{}","{}","{}","{}","{}","{}"'.format(
        surname, firstname, regNo, courseInSession, department, faculty, level)
    ser.write(to_send.encode())
    time.sleep(0.2)
    if at_send_check_response("+TEST: TXLRSTR", 5000, to_send) == 1:
        print("Sending successful")
        return 1
    else:
        print("Sending failed")
        return 0


def isNumeric(string):
    for i in range(len(string)):
        if string[i].isdigit():
            return True
    return False


def isMarked(id, marked):
    for i in range(len(marked)):
        print(marked[i])
        if marked[i] == id:
            return True
    return False


def at_send_check_response(p_ack, timeout_ms, p_cmd, *args):
    ch = 0
    recv_buf = bytearray()
    start_millis = 0
    p_cmd = p_cmd % args
    ser.write(p_cmd)
    print(p_cmd)
    time.sleep(0.2)
    start_millis = time.time()

    if p_ack is None:
        return 0

    while time.time() - start_millis < timeout_ms/1000:
        while ser.in_waiting > 0:
            ch = ser.read()
            recv_buf.append(ch)
            print(ch, end="")
            time.sleep(0.002)

        if p_ack in recv_buf:
            return 1

    return 0


def strtok(val, delim):
    token_list = []
    token_list.append(val)
    for key in delim:
        nList = []
        for token in token_list:
            subTokens = [x for x in token.split(key) if x.strip()]
            nList = nList + subTokens
        token_list = nList
    return token_list


initSetup()

# loop
while 1:
    if currentPage == PageType.MAIN_MENU:
        mainMenu()
    elif currentPage == PageType.ENROLL_MENU:
        enrollMenu()
    elif currentPage == PageType.ATTENDANCE_MENU:
        takeAttendance()
    elif currentPage == PageType.ENROLL_LECTURER:
        enrollTheLecturer()
    elif currentPage == PageType.ENROLL_STUDENT:
        enrollStudent()
        currentPage = PageType.MAIN_MENU
