# installation of opencv is a complete pain and is different on different computers/operating systems
# for windows10 this works:     conda install -c conda-forge opencv=3.2.0
# assumes data folder is in src directory named EPM or OF
# must have three other folders in these data folders - image, graph, data

from __future__ import division    # "/" always gives a real result, should include this for any math based program in Python 2.x
import os
import cv2
import numpy as np
import matplotlib.pyplot as plt
import my_utilities_OF as myutil
from scipy.stats import gaussian_kde
import sys
import pandas as pd

counters = myutil.Bunch(frame = 0, noCountour = 0, notInBox = 0, countourTooSmall = 0, multipleContours = 0)


class OF:
    def __init__(self):
        # OF box properties
        origin_x = 100      # x,y coordinates of top left hand corner of the center square of apparatus
        origin_y = 30
        centerBoxSize = 390 # size of center square of apparatus
        boxOffset = 30        # to make boundary box somewhat bigger than the floor of the apparatus in case rat rears up on walls
        self.OF_box = myutil.Bunch(x = origin_x, y = origin_y, boxSize = centerBoxSize, boffset = boxOffset)
    
    def getDimensions(self):
        return self.OF_box.x, self.OF_box.y, self.OF_box.boxSize

    def getBoxes(self):
    # updates the EPM box coordinates
        x = self.OF_box.x 
        y = self.OF_box.y
        box = self.OF_box.boxSize
        offset = self.OF_box.boffset
        b4 = int(round(box/4))  # everything has to be integer for plotting
        b8 = int(round(box/8))
        b2 = int(round(box/2))
        b34 = int(round(3*box/4))
        b38 = int(round(3*box/8))
        bb = [(x-offset, y-offset), (x+box+offset, y+box+offset)]   # boundary box, rat must be within this box
        ob = [(x, y), (x + box, y + box)]                       # outer box should match the size of floor of the apparatus
        intermediate_box = [(x+b8, y+b8), (x+b8+b34, y+b8+b34)]
        intermediate_center_box = [(x+b4, y+b4), (x+b4+b2, y+b4+b2)]
        very_center_box = [(x+b38, y+b38), (x+b38+b4, y+b38+b4)]
        return bb, ob, intermediate_box, intermediate_center_box, very_center_box



    def adjustBoxes(self, bgGray):
    # allow user to reposition/resize the boxes, break from the loop when `c` is pressed
        boxes = self.getBoxes()
        key = cv2.waitKey(1) & 0xFF
        while key != ord("c"):
            # need to continually refresh boxFrame because no other way to clear rectangle
            boxFrame = bgGray 
            boxFrame = myutil.addBoxes(boxFrame, boxes)
            cv2.putText(boxFrame, 'Press \'c\' if box position is OK', (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 1)
            cv2.imshow(file_name, boxFrame)
            if key == ord("r"): # right arrow
                self.OF_box.x = self.OF_box.x + 1
            elif key == ord("l"): # left arrow
                self.OF_box.x = self.OF_box.x - 1
            elif key == ord("u"): # up arrow
                self.OF_box.y = self.OF_box.y - 1
            elif key == ord("d"): # down arrow
                self.OF_box.y = self.OF_box.y + 1
            elif key == ord("."): # down arrow, boxSize has to be a multiple of 4
                self.OF_box.boxSize = self.OF_box.boxSize + 4
            elif key == ord(","): # down arrow, boxSize has to be a multiple of 4
                self.OF_box.boxSize = self.OF_box.boxSize - 4
         
            boxes = self.getBoxes()
            key = cv2.waitKey(5) & 0xFF 
        #  print box parameters
        print 'x = ', self.OF_box.x, 'y = ', self.OF_box.y, 'boxSize = ', self.OF_box.boxSize
        return boxes   
    
    def whichBox(self, boxedFrame, cx, cy): 
    # finds which box the rat is in
        boxes = self.getBoxes()

        bb = boxes[0]
        ob = boxes[1]
        intermediate = boxes[2]
        intermediate_center = boxes[3]
        very_center = boxes[4]

        boxText = ''    

        if very_center[0][0] <= cx <= very_center[1][0] and very_center[0][1] <= cy <= very_center[1][1]:
            cv2.rectangle(boxedFrame, very_center[0], very_center[1], (0, 0,255), 1)
            boxText = 'very_center'
        elif intermediate_center[0][0] <= cx <= intermediate_center[1][0] and intermediate_center[0][1] <= cy <= intermediate_center[1][1]:
            cv2.rectangle(boxedFrame, intermediate_center[0], intermediate_center[1], (0, 0,255), 1)
            cv2.rectangle(boxedFrame, very_center[0], very_center[1], (0, 0,255), 1)
            boxText = 'intermediate_center'
        elif intermediate[0][0] <= cx <= intermediate[1][0] and intermediate[0][1] <= cy <= intermediate[1][1]:
            cv2.rectangle(boxedFrame, intermediate[0], intermediate[1], (0, 0,255), 1)
            cv2.rectangle(boxedFrame, intermediate_center[0], intermediate_center[1], (0, 0,255), 1)
            boxText = 'intermediate'
        elif bb[0][0] <= cx <= bb[1][0] and bb[0][1] <= cy <= bb[1][1]:
            cv2.rectangle(boxedFrame, ob[0], ob[1], (0, 0,255), 1)
            cv2.rectangle(boxedFrame, intermediate[0], intermediate[1], (0, 0,255), 1)
            boxText = 'near_wall'
        else:  
            print 'Error: should not happen'          

        return boxedFrame, boxText    
    
    def ratInBox(self, cx, cy):
        boxes = self.getBoxes()
        boundarybox1 = boxes[0]
        min_x1 = boundarybox1[0][0]
        max_x1 = boundarybox1[1][0]
        min_y1 = boundarybox1[0][1]
        max_y1 = boundarybox1[1][1]
        inBox = (min_x1 <= cx <= max_x1 and min_y1 <= cy <= max_y1)
        return inBox  
    
    def getBoxText(self):
        txt = '\t' + str(self.OF_box.x) + '\t' + str(self.OF_box.y) + '\t' + str(self.OF_box.boxSize) + '\n'
        return txt   
    
    def getPlotLimits(self):
        return ([0,450],[0,400])


def findRat(camera, backgroundFrame):
# find when rat is first alone in box by testing when centroid of largest contour is within the box
    boxes = assaySpecific.getBoxes()
    noRat = True
    cnt = []     # stores 'rat' contour
    while noRat:
        (_, frame) = camera.read()
        frame, contours = myutil.findCountours(frame, backgroundFrame)

        if contours == []: # no 'rat'
            pass
        else:
            if len(contours) > 1: # more than 1 potential 'rat'
                # find largest contour with its centroid in the box in the hope that this is the rat
                oldArea = 0
                for c in contours:
                    # find centroid
                    M = cv2.moments(c)
                    cx = int(M['m10']/M['m00'])
                    cy = int(M['m01']/M['m00'])
                    if assaySpecific.ratInBox(cx, cy):
                        newArea = cv2.contourArea(c)
                        if newArea > oldArea:
                            cnt = c
                            oldArea = newArea
            else: # only 1 potential 'rat'
                cnt = contours[0]

            if cnt == []:  # deal with case where there are multiple contours but none in box so that cnt is not defined in first frame
                pass
            else:
                # find centroid
                M = cv2.moments(cnt)
                cx = int(M['m10']/M['m00'])
                cy = int(M['m01']/M['m00'])
                # test if 'rat' is in box and is big enough
                if assaySpecific.ratInBox(cx, cy) and cv2.contourArea(cnt) > myutil.min_area:
                    noRat = False
        if Single:
            frame = myutil.addBoxes(frame, boxes)
            cv2.imshow(file_name, frame)
            # if the `q` key is pressed, break from the loop
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break

def excludeTimecode(c):
    M = cv2.moments(c)
    cx = int(M['m10']/M['m00'])
    cy = int(M['m01']/M['m00'])
    if cx > timecode_x and cy < timecode_y:
        return True

def trackRat(camera, backgroundFrame):
# track rat during the rest of the video
    boxes = assaySpecific.getBoxes()
    # storage for rat location
    xList = []
    yList = []
    dataText = ''
    
# reset counters
    counters.frame = 0
    counters.noCountour = 0
    counters.countourTooSmall = 0
    counters.notInBox = 0
    counters.multipleContours = 0
    cx = 0  # initialize these coordinates to deal with the problem with the first frame
    cy = 0
    box_text = ''
    
    (grabbed, frame) = camera.read() # grab first frame in analysis period
    startFrame = camera.get(cv2.CAP_PROP_POS_FRAMES) # get number of frame at the start of the analysis period



    # perform analysis for 72 minutes
    while camera.isOpened() and grabbed and (counters.frame <= myutil.fps * 72 * 60):
        frame, contours = myutil.findCountours(frame, backgroundFrame)

        if exclude_timecode:
            contours = filter(lambda c: not excludeTimecode(c), contours)

        if not contours: # no rat

            # if no contours after mouse is in area close to home cage (or is in homecage in prev frame), 
            # then will assume mouse is in homecage; otherwise it will add 'no contour' counter and record previous frame x,y coordinates
            
            if (cy < 50 and (cx > 250 and cx < 350) and has_been_out_of_cage) or (cx == 0 and cy == 0):
                cnt = [0,0]
                cx = 0
                cy = 0
                xList.append(cx)
                yList.append(cy)
            else:
                print counters.frame, 'Warning: no contours'
                counters.noCountour = counters.noCountour + 1

        else:
            has_been_out_of_cage = True
            if len(contours) > 1: # more than 1 potential 'rat'
                counters.multipleContours = counters.multipleContours + 1
                # find largest contour with its centroid in the box in the hope that this is the rat
                # this fails if none of the contours in the first frame fall inside box and/or are big enough
                oldArea = 0

                for c in contours:
                    # find centroid
                    M = cv2.moments(c)
                    cx = int(M['m10']/M['m00'])
                    cy = int(M['m01']/M['m00'])
                    # test if 'rat' is in box and is big enough
                    if assaySpecific.ratInBox(cx, cy) and cv2.contourArea(c) > myutil.min_area:
                        newArea = cv2.contourArea(c)
                        if newArea > oldArea:
                            cnt = c
                            oldArea = newArea
                    else:
                        counters.noCountour = counters.noCountour + 1
                        cnt = c
            else: # only 1 'rat'
                cnt = contours[0]

            # Show all contours
            frame = cv2.drawContours(frame, contours, -1, (0,255,0), 3)

            # find centroid location
            M = cv2.moments(cnt)
            cx = int(M['m10']/M['m00'])
            cy = int(M['m01']/M['m00'])

            # check if 'rat' is big enough
            if cv2.contourArea(cnt) < myutil.min_area:
                print counters.frame, '  Warning: contour too small', '  area = ', cv2.contourArea(cnt)
                counters.countourTooSmall = counters.countourTooSmall + 1


        # update seconds elapsed counter on screen
        elapsedSeconds = int(round((camera.get(cv2.CAP_PROP_POS_FRAMES)-startFrame)/myutil.fps))
        cv2.putText(frame, str(elapsedSeconds), (frame.shape[1] - 65, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 1)
        

        frame = myutil.addBoxes(frame, boxes) # add boxes after checking for contours

        # if 'rat' is in box, find which box, add marker and store data
        # in the case of contours = null, previous frames values are used as best estimate
        if assaySpecific.ratInBox(cx, cy):
            frame, box_text = assaySpecific.whichBox(frame, cx, cy)     # this adds red box to image
            frame = cv2.circle(frame, (cx,cy), 2, (0,0,255), 3)     # add red dot
            dataText = dataText + str(counters.frame) + '\t' + str(cx) + '\t' + str(cy) + '\t' + box_text + '\n'
            xList.append(cx)
            yList.append(cy)
        else:
            box_text = 'home_cage'
            dataText = dataText + str(counters.frame) + '\t' + str(cx) + '\t' + str(cy) + '\t' + box_text + '\n'
            xList.append(cx)
            yList.append(cy)

        if Single:

            cv2.imshow(file_name, frame)
            # if the `q` key is pressed, break from the loop
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
        lastFrameNumber = camera.get(cv2.CAP_PROP_POS_FRAMES)-startFrame
        lastFrame = frame
        counters.frame = counters.frame + 1
        (grabbed, frame) = camera.read() # get next frame

    return dataText, xList, yList, lastFrame, lastFrameNumber

def printToConsole(counters, lastFrameNumber):
# save data file and print Warning messages to console
    print 'Warning: There were ', counters.noCountour, '(', str('%.1f' %(counters.noCountour/counters.frame*100)), '%) no contour warnings.'
    print 'Warning: There were ', counters.notInBox, '(', str('%.1f' %(counters.notInBox/counters.frame*100)), '%) not in the box warnings.'
    print 'Warning: There were ', counters.countourTooSmall, '(', str('%.1f' %(counters.countourTooSmall/counters.frame*100)), '%) contour too small warnings.'
    print 'Warning: There were ', counters.multipleContours, '(', str('%.1f' %(counters.multipleContours/counters.frame*100)), '%) occurrences of multiple contours.'

    print 'Total number of frames processed = ', counters.frame-1
    print 'Last frame number = ', int(lastFrameNumber)
    secondsProcessed = (lastFrameNumber)/myutil.fps
    print 'Seconds of video processed = ', secondsProcessed

def saveData(headerText, dataText, lastFrame, lastFrameNumber):
    headerText = headerText + 'Warning: There were ' + str(counters.noCountour) +  '(' + str('%.1f' %(counters.noCountour/counters.frame*100)) + '%) no contour warnings.' + '\n'
    headerText = headerText + 'Warning: There were ' + str(counters.notInBox) +  '(' + str('%.1f' %(counters.notInBox/counters.frame*100)) + '%) not in the box warnings.' + '\n'
    headerText = headerText + 'Warning: There were ' + str(counters.countourTooSmall) +  '(' + str('%.1f' %(counters.countourTooSmall/counters.frame*100)) + '%) contour too small warnings.' + '\n'
    headerText = headerText + 'Warning: There were ' + str(counters.multipleContours) +  '(' + str('%.1f' %(counters.multipleContours/counters.frame*100)) + '%) occurrences of multiple contours.' + '\n'
    headerText = headerText + 'Total number of frames processed = ' + str(counters.frame-1) + '\n'
    secondsProcessed = (lastFrameNumber)/myutil.fps
    headerText = headerText + 'Seconds of video processed = ' + str(secondsProcessed) + '\n'
    assayText = assaySpecific.getBoxText()
    headerText = headerText + str(counters.frame-1) + '\t' + str(counters.noCountour) + '\t' + str(counters.notInBox) + '\t' + str(counters.countourTooSmall) + '\t' + str(counters.multipleContours) + assayText

    # save data file
    with open(base_Path + 'data/' + file_name + '.txt', 'w') as f:
        f.write(headerText + dataText)
    f.close()

    # save last image to file, can check this to see if everything looks OK
    cv2.imwrite(base_Path + 'image/' + file_name + '.png', lastFrame)

def plotData(xList, yList):
# plot data and save file
    x, y, box = assaySpecific.getDimensions()
    plot_x = np.array(xList) - x
    plot_y = (np.array(yList) - y)*-1 + box   # invert y-axis to match video orientation
    xy_coordinates = zip(plot_x,plot_y)

    a=plot_x
    b=plot_y
    # Calculate the point density
    ab = np.vstack([plot_x,plot_y])
    z = gaussian_kde(ab)(ab)
    # # Sort the points by density, so that the densest points are plotted last
    idx = z.argsort()
    plot_x, plot_y, z = plot_x[idx], plot_y[idx], z[idx]

    # Create heatmap
    fig, ax = plt.subplots()
    ax.scatter(plot_x, plot_y, c=z, s=50, cmap=plt.cm.jet, edgecolor='')
    plotlimits = assaySpecific.getPlotLimits()  # get assay specific plot limits
    plt.xlim(plotlimits[0])
    plt.ylim(plotlimits[1])
    plt.savefig(base_Path + 'heatmap/' + file_name + '.png', bbox_inches='tight')  
    plt.close()


    
def processFile(base_Path, file_name, testType):
    
    noRat = True
    camera = cv2.VideoCapture(base_Path+file_name)      # open video file

    # NN: Next lines to replace getBackground function  
    imageFolder = './OF/backgroundImage/'
    date = file_name.split('_')[0]
    if os.path.exists(imageFolder + file_name + '.jpg'):
        image = imageFolder + file_name + '.jpg' 
    else:
        image = imageFolder + date + '.jpg'
    bgFrame = cv2.imread(image) # NN: reads image within backgroundImage folder
    bgGray = cv2.cvtColor(bgFrame, cv2.COLOR_BGR2GRAY) # NN: convert to grayscale
    backgroundFrame = cv2.GaussianBlur(bgGray, (myutil.ksize, myutil.ksize), 0)  ## NN: Blurs image

    print ('Running video file ' + file_name + ' using background image ' + image )
    headerText = file_name + '\n'

    if Single:  # user interaction to adjust box size, only for single files
        assaySpecific.adjustBoxes(bgGray)
    findRat(camera, backgroundFrame)       # advances through file until there is a 'rat' within the boundary boxes
    dataText, xList, yList, lastFrame, lastFrameNumber = trackRat(camera, backgroundFrame)  # track rat for 5 minutes
    printToConsole(counters, lastFrameNumber)        # print quality control stats
    saveData(headerText, dataText, lastFrame, lastFrameNumber)  # save data to file
    plotData(xList, yList) 

    # cleanup the camera and close any open windows
    camera.release() # Close the webcam
    cv2.destroyAllWindows()


base_Path = 'OF/'  
file_name = '20180612_PO_M_345__4.h264.mp4' 
testType = 'OF'


if testType == 'EPM':
    assaySpecific = EPM()
elif testType == 'OF':
    assaySpecific = OF()
 
exclude_timecode = True
timecode_x = 100
timecode_y = 25

Single = True
Multiple =  not Single

if Single:
    processFile(base_Path, file_name, testType)

# if multiple, iterate through videos and corresponding background images
elif Multiple:
    fileList = os.listdir(base_Path)
    for file_name in fileList:
        path = os.path.join(base_Path, file_name)
        if not os.path.isdir(path) and not file_name.startswith('.'): 
            processFile(base_Path, file_name, testType)