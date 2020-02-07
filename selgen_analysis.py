import pandas as pd
import cv2
import numpy as np
import scipy.ndimage
import scipy.io
import os
import re
import selgen_global

def crop_ROI(image):

    assert (type(image) == np.ndarray) & (len(image.shape) == 3) & np.amin(image) >= 0 & np.amax(image) <= 255, 'Input data has to be RGB image'

    b,g,r = cv2.split(image)

    M3 = b < 100

    mask = M3

    #sloupce
    proj = np.sum(mask, axis = 1)
    mez = max(proj)/3

    pos = round(len(proj)/2)

    while proj[pos] > mez:
        pos = pos+1

    dos = pos

    pos = round(len(proj)/2)

    while proj[pos] > mez:
        pos = pos-1

    ods = pos

    #radky
    proj = np.sum(mask,axis = 0)
    mez = max(proj)/3
    pos = round(len(proj)/2)

    while proj[pos] >mez:
        pos = pos+1

    dor = pos

    pos = round(len(proj)/2)

    while proj[pos]>mez:
        pos = pos-1

    odr = pos

    ROI = image[ods:dos, odr:dor,:]
    
    return ROI


def half_split(image):

    assert (type(image) == np.ndarray) & (len(image.shape) == 3) & np.amin(image) >= 0 & np.amax(image) <= 255, 'Input data has to be RGB image'
  
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    h,w = hsv.shape[0:2]
  
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    h,w = hsv.shape[0:2]

    lower = np.array([0,0,20])
    upper = np.array([250,100,150])

    mask = cv2.inRange(hsv, lower, upper)
    mask = (mask==0).astype('uint8')


    mask[0:200,:]=0
    mask[h-200:h,:]=0
    mask[:,0:1200]=1
    mask[:,w-1200:w]=1

    mask = (mask > 0).astype('uint8')
    proj = np.sum(mask, axis = 0)
    index  =  np.round(np.mean(np.argpartition(proj, 30)[:30]),-1).astype('uint16')
    
    left = image[:, 0:index, :]
    right = image[:, index:image.shape[1], :]

    return left, right



def find_cross_mask(image, etalon_path):

    assert (type(image) == np.ndarray) & (len(image.shape) == 3) & np.amin(image) >= 0 & np.amax(image) <= 255, 'Input data has to be RGB image'
    assert (type(etalon_path) == str) and (os.path.exists(etalon_path)), 'Path to bucket storage credentials json file is not valid'

    pattern = scipy.io.loadmat(etalon_path)

    cross_pattern = pattern['krizek']
    
    hsv = cv2.cvtColor(image.copy(), cv2.COLOR_BGR2HSV)
    
    lower = np.array([60,0,50])
    upper = np.array([140,100,155])

    background_mask = cv2.inRange(hsv, lower, upper)
    background_mask = (background_mask>0).astype('uint8')
      
    grayscale_ROI = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    ret, ROI_thresholded = cv2.threshold(grayscale_ROI,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)
    cross_mask = scipy.ndimage.correlate(ROI_thresholded, cross_pattern, mode='nearest')
    
    cross_mask = cross_mask * background_mask
    
    return cross_mask


def get_cross_grid(image, side):
    
    import numpy as np
    
    assert (type(image) == np.ndarray) & (len(image.shape) == 2) & np.amin(image) >= 0 & np.amax(image) <= 255, 'Input data has to be RGB image'
    assert side in ('left','right'), 'Side argument is string left or right'

    h,w = image.shape

    image[0:130,:] = 0
    image[h-130:h,:] = 0

    if(side == 'left'):

        image[:,0:150] = 0
        image[:,w-100:w] = 0

    if(side == 'right'):

        image[:,0:100] = 0
        image[:,w-150:w] = 0

    rows = np.sum(image, axis = 1)
    cols = np.sum(image, axis = 0)

    row_indexes = []
    col_indexes = []

    rows = list(rows)
    cols = list(cols)

    for i in range(0,7):

        index = np.argmax(cols)

        col_indexes.append(index)
        not_indexes = list(np.linspace(index-80,index+80,161))

        for it in not_indexes:
            if(0 <= int(it) <= w-1):
                cols[int(it)] = min(cols)


    for j in range(0,9):

        index = np.argmax(rows)

        row_indexes.append(index)
        not_indexes = list(np.linspace(index-80,index+80,161))

        for it in not_indexes:
            if(0 <= int(it) <= h-1):
                rows[int(it)] = min(rows)

    row_indexes.sort()
    col_indexes.sort()

    r_sum = 0
    c_sum = 0

    for i in range(1,len(row_indexes)):

        r_sum = r_sum + (row_indexes[i] - row_indexes[i-1])   

    for j in range(1,len(col_indexes)):    

        c_sum = c_sum + (col_indexes[j] - col_indexes[j-1]) 


    r_shift = r_sum //  (len(row_indexes)-1)   
    c_shift = c_sum //  (len(col_indexes)-1)

    min_r = row_indexes[0]-r_shift
    max_r = row_indexes[len(row_indexes)-1]+r_shift

    min_c = col_indexes[0]-c_shift
    max_c = col_indexes[len(col_indexes)-1]+c_shift


    min_r = max(0,min_r)
    max_r = min(max_r,h)

    min_c = max(0,min_c)
    max_c = min(max_c,w)

    row_indexes.append(min_r)
    row_indexes.append(max_r)

    col_indexes.append(min_c)
    col_indexes.append(max_c)


    row_indexes.sort()
    col_indexes.sort() 

    roww_indexes = []

    for l in range (0,len(row_indexes),2):

        roww_indexes.append(row_indexes[l])
     
    return roww_indexes,col_indexes


def split_tray(image,side,row_indexes,col_indexes):
    
    assert (type(image) == np.ndarray) & (len(image.shape) == 3) & np.amin(image) >= 0 & np.amax(image) <= 255, 'Input data has to be RGB image'
    assert side in ('left','right'), 'Side argument is string left or right'
    assert type(row_indexes) == list, 'Row_indexes argument is list of integers'
    assert type(col_indexes) == list, 'Cow_indexes argument is list of integers'

    areas = []
    
    class area():
    
        def __init__(self, side, row, column, cropped_area, size):
        
            self.side = side
            self.row = row
            self.column = column
            self.cropped_area = cropped_area
            self.size = size
            
    for i in range(0,len(row_indexes)-1):
        for j in range(0,len(col_indexes)-1):


            cropped_area = image[row_indexes[i]:row_indexes[i+1],col_indexes[j]:col_indexes[j+1],:]
            area_ = area(side,i,j,cropped_area,cropped_area.shape[0:2])
            areas.append(area_)
            
    return areas


def process_selgen_image(image):
    
    assert (type(image) == np.ndarray) & (len(image.shape) == 3) & np.amin(image) >= 0 & np.amax(image) <= 255, 'Input data has to be RGB image'
    
    roi = crop_ROI(image)
    
    left_part, right_part = half_split(roi)
    
    left_part_mask = find_cross_mask(left_part, selgen_global.etalon_path)
    right_part_mask = find_cross_mask(right_part, selgen_global.etalon_path)

    left_part_row, left_part_col = get_cross_grid(left_part_mask, 'left')
    right_part_row, right_part_col = get_cross_grid(right_part_mask, 'right')
   
    left_part_areas = split_tray(left_part,'left', left_part_row, left_part_col)
    right_part_areas = split_tray(right_part,'right', right_part_row, right_part_col)    
    
    roi_coords = (min(left_part_row[0], right_part_row[0]), max(left_part_row[len(left_part_row)-1], right_part_row[len(right_part_row)-1]) ,left_part_col[0], right_part_col[len(left_part_col)-1])

    areas = [*left_part_areas, *right_part_areas], roi_coords
    
    return areas


def segmentation_biomass(image, lower_thresh, upper_thresh):

    assert (type(image) == np.ndarray) & (len(image.shape) == 3) & np.amin(image) >= 0 & np.amax(image) <= 255, 'Input data has to be RGB image'

    h,w = image.shape[0:2]

    hsv = cv2.cvtColor(image.copy(), cv2.COLOR_BGR2HSV)

    mask = cv2.inRange(hsv, lower_thresh, upper_thresh)
    mask = (mask>0).astype('uint8')


    biomass = mask.sum() / (h*w)

    return biomass


def paint_active_biomass(image, lower_thresh, upper_thresh):

    assert (type(image) == np.ndarray) & (len(image.shape) == 3) & np.amin(image) >= 0 & np.amax(image) <= 255, 'Input data has to be RGB image'

    
    ROI = crop_ROI(image)

    hsv = cv2.cvtColor(ROI.copy(), cv2.COLOR_BGR2HSV)

    mask = cv2.inRange(hsv, lower_thresh, upper_thresh)
    mask = (mask>0).astype('uint8') * 255
    mask = cv2.Canny(mask,100,200)

    ret,cnts,jj = cv2.findContours(mask, cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)

    cv2.drawContours(ROI, cnts, -1, (0, 0, 255), 1)

    return ROI


def evaluate_selgen_batch(path):

    assert (type(path) == str), 'path should navigate into the folder where batch of images is stored'
    
    if not os.path.exists(path + 'contoured_images/'):
        os.makedirs(path + 'contoured_images/')


    if not os.path.exists(path + 'failed/'):
        os.makedirs(path + 'failed/')
         
    formats = ('.JPG','.jpg','.PNG','.png','.bmp','.BMP','.TIFF','.tiff','.TIF','.tif')
    files = [file for file in os.listdir(path) if file.endswith(formats)]
    data = []   
        
    for file in files:
        
        try:
    
            image = cv2.imread(path+file)

            areas, roi_coords = process_selgen_image(image)

            roi = image[roi_coords[0]:roi_coords[1],roi_coords[2]:roi_coords[3],:]

            contoured_image = paint_active_biomass(roi, selgen_global.lower_thresh, selgen_global.upper_thresh)

            cv2.imwrite(path + 'contoured_images/' + file, contoured_image)

            for area in areas:
                
                biomass = segmentation_biomass(area.cropped_area, selgen_global.lower_thresh, selgen_global.upper_thresh)

                info  = file.split('.')
                regex = re.match('(^\d+)([a-z])', info[0])
                day = regex.group(1)  
                variant = regex.group(2)
                
                side = area.side
                row = area.row
                column = area.column
                size = area.size

                data.append(dict(zip(('variant','day','side','row', 'column','biomass', 'size'),(variant, day, side, row, column, biomass, size))))
            
            print('{} was succesfully processed'.format(file))

        except Exception as e:
            
            cv2.imwrite(path + 'failed/' + file, image)

            raise e
                
    df = pd.DataFrame(data)
    df.to_excel(path + 'contoured_images/' + 'batch_output.xlsx')