from flask import Flask, request, jsonify
import base64
import imutils
import os
from PIL import Image
import face_recognition
from io import BytesIO
import cv2
import numpy as np
import json
from flask import Flask
from bson import ObjectId
import re
from pymongo import MongoClient
from imutils import paths

app = Flask(__name__)

username = "thinalpethiyagoda"
password = "321t071np"
dbname = "universitysystem"
cluster = "universitysystem.009rjim.mongodb.net"

connection_string = "mongodb+srv://thinalpethiyagoda:321t071np@universitysystem.009rjim.mongodb.net/"



client = MongoClient(connection_string)
db = client["universitysystem"]
collection = db["lecturers"]
collection2 = db["students"]
collection3 = db["modules"]
collection4 = db["lectures"]
collection5 = db["attendance"]
collection6 = db["profile_pic"]

script_dir = os.path.dirname(os.path.abspath(__file__))

encodingsP = os.path.join(script_dir, "faces.json")
cascade = os.path.join(script_dir, "haarcascade_frontalface_default.xml")
datasetP = os.path.join(script_dir, "dataset")
currentname = "unknown"



with open(encodingsP, "r") as file:
    data = json.load(file)
detector = cv2.CascadeClassifier(cascade)

@app.route('/')
def index():
    return 'Welcome to my Flask app!'

@app.route('/create-lecturer', methods=['POST'])
def create_lecturer():
    try:
        data = request.get_json()
        name = data.get('name')
        password = data.get('password')

        
        lecturer_count = collection.count_documents({})

        
        lecturer_id = lecturer_count

        
        lecturer = {
            'name': name,
            'password': password,
            'lecturer_id': lecturer_id
        }
        collection.insert_one(lecturer)

        return jsonify({'message': 'Lecturer created successfully', 'lecturer_id': lecturer_id}), 200
    except Exception as e:
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500

@app.route('/create-module', methods=['POST'])
def create_module():
    try:
        data = request.get_json()
        module_code = data.get('module_code')
        module_name = data.get('module_name')
        lecturer_id = int(data.get('lecturer_id'))  
        number_of_lectures = int(data.get('number_of_lectures'))  

        
        module = {
            'module_code': module_code,
            'module_name': module_name,
            'lecturer_id': lecturer_id,
        }
        module = collection3.insert_one(module)

     
        for i in range(1, number_of_lectures + 1):
            lecture_id = f'{module_code}{i}'  
            title = f'Lecture {i}'
            lecture = {
                'lecture_id': lecture_id,
                'module_code': module_code,
                'title': title,
                'attendance_status': 'none'
            }
            collection4.insert_one(lecture)

        return jsonify({'message': 'Module and lectures created successfully'}), 200
    except Exception as e:
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500



@app.route('/confirm-attendance', methods=['POST'])
def confirm_attendance(): 
    try:
        data = request.get_json()
        lecture_id = data.get('lecture_id')
        recorded_names = data.get('recorded_names')
        
        for name in recorded_names:
            user = collection2.find_one({'name': name})
            record = {
                'lecture_id': lecture_id,
                'student_id': user['student_id'],
                'attendance_status': 'present'  
            }
            collection5.insert_one(record)
        collection4.update_one({'lecture_id': lecture_id}, {'$set': {'attendance_status': 'Confirmed'}})
        return jsonify({'message': 'Attendance confirmed successfully'}), 200
    except Exception as e:
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    user = collection.find_one({'name': username, 'password': password})
    if user:
        return jsonify({'message': 'Login successful', 'lecturer_id': str(user['lecturer_id'])}), 200
    else:
        return jsonify({'error': 'Invalid username or password'}), 401




@app.route('/search-students', methods=['POST'])
def search_students():
    try:
        data = request.get_json()
        search_query = data.get('searchQuery')
        
        # Check if the search query is a digit (student ID)
        if search_query.isdigit():
            students = collection2.find({"$or": [
                {"student_id": int(search_query)},
                {"name": {"$regex": search_query, "$options": "i"}}
            ]})
        else:
            # Search by name
            students = collection2.find({"name": {"$regex": search_query, "$options": "i"}})
        
        search_results = []
        for student in students:
            student_info = {
                'student_id': str(student.get('student_id')),
                'name': student.get('name'),
                'disciplinary_issues': student.get('disciplinary_issues'),
                'existing_conditions': student.get('existing_conditions')
            }
            search_results.append(student_info)
        
        return jsonify(search_results), 200
    except Exception as e:
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500




@app.route('/get-studentattendance',methods=['POST'])
def get_student_attendance():
    
    data = request.get_json()
    student_id = data.get('student_id')
    student_id = int(student_id)
    modules_list = collection3.find()
    modules= list(modules_list)
    module_attendance = []
    for module in modules:
        total_attended = 0
        print(module['module_code'])
        lectures = collection4.find({'module_code': module['module_code'], 'attendance_status': 'Confirmed'})
        total_lectures = 0
        for lecture in lectures:
            total_lectures += 1
            attendance_records = collection5.find({'student_id': student_id,'lecture_id': lecture['lecture_id']})
            attendance = len(list(attendance_records))
            print(list(attendance_records))
            if attendance > 0:
                total_attended += 1
        if total_lectures == 0:
            attendance_percentage = 0;  
        else:
            attendance_percentage = (total_attended / total_lectures) * 100
        
        module['_id'] = str(module['_id'])  
        module_attendance.append(attendance_percentage)
    student = collection2.find_one({'student_id': student_id})
    images =collection6.find_one({'name': student['name']})
    return jsonify({'modules': modules, 'module_attendance': module_attendance,'disciplinary_issues':student['disciplinary_issues'], 'existing_conditions':student['existing_conditions'],'gpa':student['gpa'],'profile_pic_base64': images['image']}), 200


    
@app.route('/edit_attendance', methods=['POST'])
def edit_attendance():
    try:
        data = request.get_json()
        student = data.get('student')
        lecture_id = data.get('lecture_id')
        if any(char.isdigit() for char in student):
            student = int(student)
            print(student)
            user = collection2.find_one({'student_id': student})
            record = {
                    'lecture_id': lecture_id,
                    'student_id': user['student_id'],
                    'attendance_status': 'present'  
                }
        else:
            user = collection2.find_one({'name': student})
            record = {
                    'lecture_id': lecture_id,
                    'student_id': user['student_id'],
                    'attendance_status': 'present'  
                }
        collection5.insert_one(record)
        return jsonify({'message': 'Attendance edited successfully'}), 200
    except Exception as e:
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500


@app.route('/modules', methods=['POST'])
def get_modules():
    data = request.get_json()
    lecturer_id = int(data.get('lecturerId')) 
    modules = collection3.find({'lecturer_id': lecturer_id}, {'_id': 0, 'module_code': 1, 'module_name': 1})
    modules_list = list(modules)
    return jsonify(modules_list)

@app.route('/lectures', methods=['POST'])
def get_lectures():
    data = request.get_json()
    module_id = data.get('module') 
    lectures = collection4.find({'module_code': module_id}, {'_id': 0, 'module_code': 1, 'title': 1, 'lecture_id' : 1, 'attendance_status': 1})
    lectures_list = list(lectures)
    return jsonify(lectures_list)

def get_condition_from_database(name):
    student = collection2.find_one({'name': name})
    if student:
        return student
    else:
        return 'none'
    
@app.route('/add_student', methods=['POST'])
def add_student():
    data = request.json
    student_name = data.get('name')
    student_profile_pic = data.get('profilePic')
    training_data = data.get('trainingData')
    disciplinary_issues = data.get('disciplinaryIssues')
    existing_conditions = data.get('existingConditions')
    gpa = float(data.get('gpa'))
    student_id = int(data.get('studentId'))

    new_folder_path = os.path.join(datasetP, student_name)
    os.makedirs(new_folder_path, exist_ok=True)

    for i, img_data in enumerate(training_data):
        img_path = os.path.join(new_folder_path, f"training_{i}.jpg")
        save_image(img_path, img_data)

    imagePaths = list(paths.list_images(datasetP))

    knownEncodings = []
    knownNames = []

    for (i, imagePath) in enumerate(imagePaths):

        print("[INFO] processing image {}/{}".format(i + 1, len(imagePaths)))
        name = imagePath.split(os.path.sep)[-2]


        image = cv2.imread(imagePath)
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)


        boxes = face_recognition.face_locations(rgb, model="hog")


        encodings = face_recognition.face_encodings(rgb, boxes)


        for encoding in encodings:
            knownEncodings.append(encoding.tolist())
            knownNames.append(name)


    print("[INFO] serializing encodings...")
    data = {"encodings": knownEncodings, "names": knownNames}
    with open(encodingsP, "w") as f:
        json.dump(data, f)
    record = {
                'student_id': student_id,
                'name': student_name,
                'disciplinary_issues': disciplinary_issues,
                'existing_conditions': existing_conditions,
                'gpa': gpa
            }
    
    collection2.insert_one(record)

    record2 = {
                'name': student_name,
                'image': student_profile_pic
            }
    collection6.insert_one(record2)
    
    return jsonify({'message': 'Student added successfully'})

def save_image(file_path, base64_data):
    with open(file_path, "wb") as f:
        f.write(base64.b64decode(base64_data))
        print("Image saved successfully")


def process_frame(base64_frame,width, height):
    global currentname
    try:
        frame_bytes = base64.b64decode(base64_frame)
        frame_array = np.frombuffer(frame_bytes, dtype=np.uint8)
        frame = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)

        frame = imutils.resize(frame, width=width, height=height)

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rects = detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30), flags=cv2.CASCADE_SCALE_IMAGE)
        boxes = [[y, x + w, y + h, x] for (x, y, w, h) in rects]
        encodings = face_recognition.face_encodings(rgb, boxes)
        names = []
        

        for encoding in encodings:
            matches = face_recognition.compare_faces(data["encodings"], encoding)
            name = "Unknown"
            if True in matches:
                matchedIdxs = [i for (i, b) in enumerate(matches) if b]
                counts = {}
                for i in matchedIdxs:
                    name = data["names"][i]
                    counts[name] = counts.get(name, 0) + 1
                name = max(counts, key=counts.get)
                if currentname != name:
                    currentname = name
            
            names.append(name)
            
        return names, boxes
    except Exception as e:
        return str(e)


@app.route("/process-frame", methods=["POST"])
def receive_frame():
    try:
        data = request.get_json()
        base64_frame = data.get("base64Frame")
        width = data.get("width")  
        height = data.get("height") 
        result = process_frame(base64_frame, width, height)
        conditions = []
        issues = []
        student_ids = []
        
        
        if result is not None:
            names, boxes = result
            boxes = [[int(y) for y in x] for x in boxes]

            for name in names:
                if name == 'Unknown':
                    conditions.append('none')
                    issues.append('none')
                    continue
                student = get_condition_from_database(name)
                student_ids.append(student['student_id'])
                conditions.append(student["existing_conditions"])
                issues.append(student["disciplinary_issues"])
            

            return jsonify({'ids':student_ids,"names": names, "boxes": boxes, "conditions": conditions, "issues": issues})
        else:
            return jsonify({"error": "No faces recognized in the frame."}), 404
        
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500




if __name__ == "__main__":
    app.run(host='0.0.0.0', port=os.environ.get('PORT', 3000), debug=True)
