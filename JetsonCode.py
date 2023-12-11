#!/usr/bin/env python3
from pathlib import Path # Already Installed with Python 3.8.10 on Jetson Xavier NX using JetPack 5.0.2
from types import SimpleNamespace # Already Installed with Python 3.8.10 on Jetson Xavier NX using JetPack 5.0.2
import argparse # Already Installed with Python 3.8.10 on Jetson Xavier NX using JetPack 5.0.2
import logging # Already Installed with Python 3.8.10 on Jetson Xavier NX using JetPack 5.0.2
import json # Already Installed with Python 3.8.10 on Jetson Xavier NX using JetPack 5.0.2
import cv2 # Already Installed with Python 3.8.10 on Jetson Xavier NX using JetPack 5.0.2
import time # Already Installed with Python 3.8.10 on Jetson Xavier NX using JetPack 5.0.2
import serial # Installed Manually
import fastmot # Installed Manually and found in the FastMOT directory
import fastmot.models # Installed Manually and found in the FastMOT directory
from fastmot.utils import ConfigDecoder, Profiler # Installed Manually and found in the FastMOT directory

def main():
  parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
  optional = parser._action_groups.pop()
  required = parser.add_argument_group('required arguments')
  group = parser.add_mutually_exclusive_group()
  required.add_argument('-i', '--input-uri', metavar="URI", required=True, help=
  'URI to input stream\n'
  '1) image sequence (e.g. %%06d.jpg)\n'
  '2) video file (e.g. file.mp4)\n'
  '3) MIPI CSI camera (e.g. csi://0)\n'
  '4) USB camera (e.g. /dev/video0)\n'
  '5) RTSP stream (e.g. rtsp://<user>:<password>@<ip>:<port>/<path>)\n'
  '6) HTTP stream (e.g. http://<user>:<password>@<ip>:<port>/<path>)\n')
  optional.add_argument('-c', '--config', metavar="FILE",default=Path(__file__).parent / 'cfg' / 'mot.json',help='path to JSON configuration file')
  optional.add_argument('-m', '--mot', action='store_true', help='run multiple object tracker')
  group.add_argument('-q', '--quiet', action='store_true', help='reduce output verbosity')
  group.add_argument('-v', '--verbose', action='store_true', help='increase output verbosity')
  parser._action_groups.append(optional)
  args = parser.parse_args()
  logging.basicConfig(format='%(asctime)s [%(levelname)8s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S') # Setup logging
  logger = logging.getLogger(fastmot.__name__)
  if args.quiet:
    logger.setLevel(logging.WARNING)
  elif args.verbose:
    logger.setLevel(logging.DEBUG)
  else:
    logger.setLevel(logging.INFO)
  # Load config file
  with open(args.config) as cfg_file:
    config = json.load(cfg_file, cls=ConfigDecoder, object_hook=lambda d: SimpleNamespace(**d))

  stream = fastmot.VideoIO(config.resize_to, args.input_uri, None, **vars(config.stream_cfg)) # Defining the video stream from the webcam
  ard=serial.Serial(port='/dev/ttyUSB0',baudrate=115200,timeout=0.1) # Defining the serial port used for communicating with the Arduino
  
  mot = fastmot.MOT(config.resize_to, **vars(config.mot_cfg), draw=False) # Defining an instance of the mot tracker
  mot.reset(stream.cap_dt) # Resets the tracker
  cv2.namedWindow('Video', cv2.WINDOW_AUTOSIZE) # Define the window showing the video stream
  
  logger.info('Starting video capture...')
  global tid #Integer variable that holds the target ID of the human body that will be tracked by the robot
  global there #Boolean variable that specifies if there is a body being tracked by the robot still in the frame
  tid = -1
  stream.start_capture()

  try:
   with Profiler('app') as prof:
     while cv2.getWindowProperty('Video', 0) >= 0:
       frame = stream.read() # Reading the frame
       if frame is None:
         break
  
       if args.mot:
         mot.step(frame) # Running the tracker on the current frame
         boxes=list()
         for track in mot.visible_tracks(): #Looping over tracked body’s boxes in the frame
           tl = track.tlbr[:2] / config.resize_to * stream.resolution #List holding the top left coordinates of the tracked body box
           br = track.tlbr[2:] / config.resize_to * stream.resolution #List holding the bottom right coordinates of the tracked body box
           x1=int(tl[0]) # Variable holding the X coordinate of the top left point for the tracked body’s box
           y1=int(tl[1]) # Variable holding the Y coordinate of the top left point for the tracked body’s box
           x2=int(br[0]) # Variable holding the X coordinate of the bottom right point for the tracked body’s box
           y2=int(br[1]) # Variable holding the Y coordinate of the bottom right point for the tracked body’s box
           if x1<0:
             x1=0
           elif x1>640:
             x1=640
           if x2<0:
             x2=0
           elif x2>640:
             x2=640
           if y1<0:
             y1=0
           elif y1>480:
             y1=480
           if y2<0:
             y2=0
           elif y2>480:
             y2=480
           width=x2-x1 # Variable holding the width for the tracked body’s box
           height=y2-y1 # Variable holding the height for the tracked body’s box
           box=[track.trk_id,x1,y1,x2,y2]
           boxes.append(box)
           startp=(x1,y1)
           endp=(x2,y2)

  if there==False: # Show tracking boxes of all the human bodies in the frame
    frame = cv2.rectangle(frame,startp,endp,(0,255,0),2)
    cv2.putText(frame,str(track.trk_id),(int(x1+width/2),int(y1+height/2)),cv2.FONT_HERSHEY_SIMPLEX,0.9,(0,255,0),2)
  else: # Show the tracking box of the human body selected to be tracked by the robot
    if track.trk_id==tid:
      frame = cv2.rectangle(frame,startp,endp,(0,255,0),2)
      cv2.putText(frame,str(track.trk_id),(int(x1+width/2),int(y1+height/2)),cv2.FONT_HERSHEY_SIMPLEX,0.9,(0,255,0),2)
  
  cv2.imshow('Video', frame) # Show the frame in the window
  if cv2.waitKey(1) & 0xFF == 27: # Break out of the tracking loop if the "Esc" button is pressed
    break

  cv2.setMouseCallback('Video', click_event,boxes) # Calling the click_event_boxes function that returns the clicked body’s tracking ID in the variable
  tid (Defined later on in the code)
  there=False
  if tid != -1:
    for track in mot.visible_tracks():
      if track.trk_id==tid:
        tl = track.tlbr[:2] / config.resize_to * stream.resolution
        br = track.tlbr[2:] / config.resize_to * stream.resolution
        x1=int(tl[0])
        y1=int(tl[1])
        x2=int(br[0])
        y2=int(br[1])
        if x1<0:
          x1=0
        if x1>640:
          x1=640
        if x2<0:
          x2=0
        if x2>640:
          x2=640
        if y1<0:
          y1=0
        if y1>480:
          y1=480
        if y2<0:
          y2=0
        if y2>480:
          y2=480
        width=x2-x1 # Variable holding the width for the tracked body’s box
        height=y2-y1 # Variable holding the height for the tracked body’s box
        string='X{0:d}Y{1:d}H{2:d}'.format((x1+width//2),(y1+height//2),height) #Define the string containing the
        centre of the selected human body box to be tracked by the robot
        ard.write(string.encode('utf-8')) # Sending the coordinated to the arduino
        there=True
        break
    else:
      there=False
    if there == False or tid == -1: # Send to the arduino to stop the robot if the selected human body is no longer in the frame
      string='X320Y240' # Sending the coordinates of the centroid for the frame which indicates to stop tracking (moving) with the robot
      ard.write(string.encode('utf-8'))

  finally: # Release the webcam stream and destroy all windows generated by the code after leaving the tracking loop
    stream.release()
    cv2.destroyAllWindows()

# Timing statistics
 if args.mot:
   avg_fps = round(mot.frame_count / prof.duration)
   logger.info('Average FPS: %d', avg_fps)
   mot.print_timing_info()

def click_event(event, x, y, flags, boxes):
  global tid #integer variable that holds the target ID of the human body that will be tracked by the robot
  global there #boolean variable that specifies if there is a body being tracked by the robot still in the frame
  flag=False
  if event == cv2.EVENT_RBUTTONDOWN: #detecting a right mouse button click to reset and stop tracking anybody
    there=False
    tid=-1
  if event == cv2.EVENT_LBUTTONDOWN: #detecting a left mouse button click to select a human body in the frame to track
    for box in boxes:
      if (x>=box[1] and x<=box[3]) and (y>=box[2] and y<=box[4]):
        flag=True
        tid=box[0]
        print("Target Selected",tid)
        break
      else:
        tid=-1


if __name__ == '__main__':
  main()
