import modules.keet_database as kdb
import cv2
import pandas as pd
import tensorflow as tf
import joblib
from sklearn.preprocessing import StandardScaler
from sklearn.preprocessing import LabelEncoder
import numpy as np
import time 
import mediapipe as mp
import modules.basic_voice_system as bvs
from modules.loaders import ModelLoaderSigns, ModelLoaderFace




############################################################################################################*

##########* LOAD THE MODEL of signs ################################
loader = ModelLoaderSigns(model_name='all_statics_model.h5', scaler_name='all_statics_scaler.pkl')
model = loader.load_sign_model()
scaler = loader.load_sign_scaler()

dict_labels = {0: 'A', 1:'B', 2:'C', 3:'D', 4:'E', 5:'F', 6:'G', 7:'H', 8:'I', 9:'L', 10:'M', 11:'N', 12:'O', 13:'P', 14:'R', 15:'S', 16:'T', 17:'U', 18:'V', 19:'W', 20:'Y'}
start_time = time.time()
delay_time = 1
predicted = False
phrase = ''
n_letters = 0
#######* LOAD THE MODEL of faces ################################
loader_face = ModelLoaderFace(model_name='face_model.h5', scaler_name='scaler_faces.pkl')
model_faces = loader_face.load_face_model()
scaler_faces = loader_face.load_face_scaler()
dict_labels_faces = {0: 'ENOJO', 1: 'FELIZ', 2: 'NEUTRAL', 3: 'SORPRESA', 4: 'TRISTE'}
predicted_face = False

#########* CAMERA SETTINGS ###########

cap, width, height = kdb.camera_settings(width_cam= 1280, height_cam= 720, camera=0) #* Width and height of the camera
                                                                                    #* 0 for the default camera, 1 for the external camera	 

#########* PARAMETERS ###########

imgformat, dataformat, tiempo_de_espera, ventana_de_tiempo = kdb.format(imgformat = 'jpg', dataformat= 'csv', waiting_time= 3, record_time = 2)

##########* Begin parameters ################# 

time_frames, t, t1, timeflag = kdb.time_set()

num_hand = 1 ### change this for the number of hands to detect

mpHands, hands, mpDraw = kdb.hand_medipip(num_hand)

window_move = kdb.wind_move(roi1_x=0.1, roi1_y=0.4, roi2_x=0.1, roi2_y=0.6) #*FIRTS ARGUMENT FOR ROI 1 AND THE SECOND FOR ROI 2

cTime, pTime, fps, Ts, time_frames = kdb.frame_settings()

#####* MEDIAPIPE FACE MESH ########

mp_face_mesh = mp.solutions.face_mesh
face_mesh_images = mp_face_mesh.FaceMesh(static_image_mode=False, max_num_faces=2, min_detection_confidence=0.5)
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles

###################* While loop for tracking    #################  

while True:
    
    current_time = time.time()
    
    ret, frame, frame_copy, frame_gray, frame_equali, results = kdb.read_frames(cap,hands,equali=True)
    #######* HAND EXTRACTION ########
    roi_save, save_len, point_save, lm_x_h1, lm_y_h1, lm_x_h2, lm_y_h2, lm_x_h1_roi, lm_y_h1_roi, lm_x_h2_roi, lm_y_h2_roi, flag = kdb.process_hand_landmarks(frame_equali= frame_equali,
                                                    results= results, width= width, height= height, t= t,tiempo_de_espera= tiempo_de_espera
                                                    ,save_len = None,print_lm=False, size_roi = 0.087, point_save={})       
    ################* FACE MESH ############	
    face_mesh_results = face_mesh_images.process(frame)
    
    if face_mesh_results.multi_face_landmarks:
        lm = face_mesh_results.multi_face_landmarks[0]  # Solo usar la primera cara detectada
        landmarks = lm.landmark
        # Extraer las posiciones de los landmarks
        positions_x = np.array([landmark.x for landmark in landmarks])
        positions_y = np.array([landmark.y for landmark in landmarks])

        # Calcular el rectángulo alrededor de la cara
        min_x, min_y = np.min(positions_x), np.min(positions_y)
        max_x, max_y = np.max(positions_x), np.max(positions_y)

        # Dibujar el rectángulo alrededor de la cara
        cv2.rectangle(frame, (int(min_x * width), int(min_y * height)),
                      (int(max_x * width), int(max_y * height)), (0, 0, 255), 3)
        
        flag_face = 1
    else:
        flag_face = 0 

    #############* REAL TIME MODEL FACE #########
    if current_time - start_time >= delay_time:  
        if flag_face == 1:
            data_face = np.concatenate([
                np.reshape(positions_x, (468, 1)),
                np.reshape(positions_y, (468, 1))
            ], axis=1)
            data_face = data_face.reshape(1, 936)
            data_normalized_face = scaler_faces.transform(data_face)
            predictions_face = model_faces.predict(data_normalized_face, verbose=0)
            predicted_class_face = np.argmax(predictions_face, axis=1)
            predictions_face = dict_labels_faces[predicted_class_face[0]]
            predicted_face = True  # Se realizó una predicción
        # start_time = current_time
    # Mostrar la predicción si se ha realizado
    if predicted_face:
        cv2.putText(frame, predictions_face, (20, 150), cv2.FONT_HERSHEY_SIMPLEX, 2, (50, 50, 200), 2)

        
    #####* REAL TIME MODEL HAND #########
    if current_time - start_time >= delay_time:  
        if flag == 1:
            if n_letters == 0:
                phrase = ''
            n_letters += 1
            data =  [ np.reshape(np.array(list(lm_x_h1.values())),(21,1))
                     , np.reshape(np.array(list(lm_x_h1_roi.values())),(21,1)), 
                      np.reshape(np.array(list(lm_y_h1.values())),(21,1)), 
                      np.reshape(np.array(list(lm_y_h1_roi.values())),(21,1)),]      
            data = np.concatenate(data,axis=1)
            data = data.reshape(1, 84)
            data_normalized = scaler.transform(data)
            predictions = model.predict(data_normalized, verbose=1)
            predicted_class = np.argmax(predictions, axis=1)
            # print(f'Predicción: {dict_labels[predicted_class[0]]}') 
            prediction = dict_labels[predicted_class[0]]
            predicted = True
            phrase = phrase + prediction
        else:
            if n_letters > 0:
                bvs.sintetizar_emocion('emocion=' + str(), texto = phrase )
                predicted = False
                n_letters = 0
        start_time = current_time    
    if predicted == True and point_save != {}:
        cv2.putText(frame, prediction, (point_save['h1_x_max'], point_save['h1_y_min']-40), cv2.FONT_HERSHEY_SIMPLEX, 2, (50, 50, 200), 3)
        cv2.putText(frame, phrase , (point_save['h1_x_max'], point_save['h1_y_min']+50), cv2.FONT_HERSHEY_SIMPLEX, 2, (50, 50, 200), 3)

    ##########* ENDS IF ##############
        
    cTime, fps, Ts, pTime, time_frames = kdb.ends_if(cTime, fps, Ts, pTime, time_frames)
        

    ################* DRAW RECTANGULOS and text ###############

    kdb.draw_text_and_rectangles(point_save, frame, width, height, fps, draw_rectangules=True,draw_text=True)

    ##############* SHOW THE FRAMES #############

    SAVED = kdb.main_show(frame = frame, SAVED = None, width= width, height=height, roi_save= roi_save, window_move= window_move, df = None, RECORDING = None, t1 = None, save_len = None, show_rois = False)
        
    #####* RESET THE LIST ########

    roi_save, point_save= kdb.reset_save(roi_save)

    ###* EXIT
        
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break   #press q for exit
cap.release()
cv2.destroyAllWindows()
