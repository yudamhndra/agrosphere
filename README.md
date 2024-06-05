# Plant Disease Detection and Early Warning System Using AIoT-Based Autonomous Vehicles

This project aims to develop a system for detecting plant diseases and providing early warnings using autonomous vehicles based on the AIoT (Artificial Intelligence of Things) concept. The system comprises several components, including a Django web application, a RESTful API, an autonomous vehicle (IoT) equipped with an ESP32-CAM, and an Android app.

## Features

- **Web Application (Django):**
  - Frontend built with HTML, CSS, Bootstrap, and JavaScript
  - Backend powered by Django
  - SQLite3 database for data storage
- **RESTful API:** Provides an interface for the autonomous vehicle (IoT) to communicate with the server.
- **Autonomous Vehicle (IoT):** Equipped with an ESP32-CAM for capturing plant images and connecting to the server via the RESTful API.
- **Android App (Kotlin):** Allows users to monitor the system and receive alerts on their Android devices.
- **AI Model (YOLOv8):** Utilizes the YOLOv8 object detection model (in .pt format) for plant disease detection.

## Installation

1. Clone the repository (highly recommended to use the 'yuda' branch which has minimum issues):

   ```bash
   git clone https://github.com/yudamhndra/agrosphere.git
   ```

2. Install the required dependencies for the Django web application:

   ```bash
   cd agrosphere
   pip install -r requirements.txt
   ```

3. Set up the database and run the Django development server:

   ```bash
   python manage.py migrate
   python manage.py runserver
   ```

4. For autonomous vehicle (IoT) components and Android applications, see the respective documentation in the repository https://github.com/KevinAS28/AgroSphere.git.

## Usage

1. Access the web application through your web browser at `http://localhost:8000`.
2. Configure and set up the autonomous vehicle (IoT) and Android app components according to the provided instructions.
3. The autonomous vehicle will capture plant images, send them to the server for disease detection, and the system will provide early warnings if necessary.
4. Users can monitor the system and receive alerts through the Android app.

## Achievements
This project won Second Place at the Olimpiade Vokasi Indonesia (OLIVIA) 2023 in the field of Smart Systems: Smart Applications.
<img src="https://github.com/yudamhndra/yudamhndra/blob/main/Image/sertif_olivia.jpg">

## Contributing

Contributions are welcome! If you find any issues or have suggestions for improvements, please open an issue or submit a pull request.

## More About AgroSphere

The following is a short video regarding the implementation of agrosphere: 
https://drive.google.com/file/d/1dVEJ3modKd9sBD6BBof_8Mldh4AZOM7g/view?usp=sharing
