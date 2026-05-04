import cv2
import numpy as np
import glob

CHECKERBOARD = (4, 7)

def calibrate_fisheye(image_folder, K_out, D_out):
    objp = np.zeros((1, CHECKERBOARD[0] *CHECKERBOARD[1], 3), np.float32)
    objp[0, :, :2] = np.mgrid[0:CHECKERBOARD[0], 0:CHECKERBOARD[1]].T.reshape(-1,2)
    
    objpoints = []
    imgpoints = []
    
    images = glob.glob(f"{image_folder}/*.jpg")
    gray_shape = None
    
    criteria = (
        cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER,
        30,
        0.0001,
    )
    
    for fname in images:
        img = cv2.imread(fname)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray_shape = gray.shape[::-1] #reverse the tuple [start : end : step]
        
        found, corners = cv2.findChessboardCorners(gray, CHECKERBOARD, None)
        print("processing:", fname)
        if not found:
            print("skipping", fname)
            continue
        corners2 = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
        
        objpoints.append(objp)
        imgpoints.append(corners2)
        print("using", fname)
        
    if len(objpoints) < 10:
        raise RuntimeError(f"Need at least 10 good images, got {len(objpoints)}")
        #stop the program throw an error
    # camera matrix
    K2 = np.zeros((3 ,3))
    D2 = np.zeros((4, 1))
    rvecs = []
    tvecs = []
    
    rms, K2, D2, rvecs, tvecs = cv2.fisheye.calibrate(
        objpoints,
        imgpoints,
        gray_shape,
        K2,
        D2,
        rvecs,
        tvecs,
        cv2.fisheye.CALIB_RECOMPUTE_EXTRINSIC
        #+ cv2.fisheye.CALIB_CHECK_COND
        + cv2.fisheye.CALIB_FIX_SKEW,
        criteria,
    )
    
    print("RMS error:", rms)
    print("K:\n", K2)
    print("D:\n", D2)
    
    np.save(K_out, K2)
    np.save(D_out, D2)

calibrate_fisheye("calbrate_cam2", "K2.npy", "D2.npy")
#calibrate_fisheye("calibrate_top", "K_top.npy", "D_top.npy")
#calibrate_fisheye("calibrate_bot", "K_bot.npy", "D_bot.npy")