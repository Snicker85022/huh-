"""3D world <-> 2D camera math for the kitchen vision system.

Coordinate system (world): X=east (ft), Y=up (ft), Z=south (ft). Origin = NW floor.
Cameras: position + yaw/pitch/roll + pinhole intrinsics K.
Yaw = rotation about Y axis (0 = looking north/-Z? define below).
Pitch = rotation about X (positive = looking down).
"""
import numpy as np
import cv2

def R_yaw(yaw_deg):
    a = np.radians(yaw_deg)
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]], float)

def R_pitch(pitch_deg):
    a = np.radians(pitch_deg)
    c, s = np.cos(a), np.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]], float)

def R_roll(roll_deg):
    a = np.radians(roll_deg)
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], float)

class Camera:
    def __init__(self, name, pos_ft, yaw_deg=0, pitch_deg=0, roll_deg=0,
                 K=None, image_size=(1280, 720)):
        self.name = name
        self.pos = np.array(pos_ft, float)          # X,Y,Z in feet
        self.yaw = yaw_deg; self.pitch = pitch_deg; self.roll = roll_deg
        self.image_size = image_size
        if K is None:
            fx = 900.0   # PTZ focal at wide zoom (from junction pole geometry ~3.4deg over 54px); refine with ruler
            cx, cy = image_size[0]/2, image_size[1]/2
            K = np.array([[fx, 0, cx], [0, fx, cy], [0, 0, 1]], float)
        self.K = K

    def R(self):
        # world -> camera rotation. Camera optical axis is +Z_c.
        R = R_roll(self.roll) @ R_pitch(self.pitch) @ R_yaw(self.yaw)
        return R

    def project(self, p_ft):
        """World point (ft) -> pixel (u,v). Returns None if behind camera."""
        pc = self.R() @ (np.array(p_ft, float) - self.pos)
        if pc[2] <= 0:
            return None
        uv = self.K @ (pc / pc[2])
        return uv[0], uv[1]

    def backproject(self, u, v):
        """Pixel -> unit ray direction in world coords."""
        kinv = np.linalg.inv(self.K)
        dir_cam = kinv @ np.array([u, v, 1.0])
        dir_cam /= np.linalg.norm(dir_cam)
        return self.R().T @ dir_cam

def triangulate_rays(origin1, dir1, origin2, dir2):
    """Closest-point midpoint of two rays."""
    A = np.array([dir1, -dir2]).T
    b = origin2 - origin1
    t, _ = np.linalg.lstsq(A, b, rcond=None)[0]
    p1 = origin1 + t * dir1
    return p1

def infer_yaw_pitch(cam_pos_ft, pts3d_ft, uv_px, K, image_size):
    """Estimate camera yaw/pitch from 3D points and their pixel locations.

    Uses the angular model: pixel offset from center -> angle = atan((u-cx)/fx).
    Compares with true azimuth/elevation of each 3D point from the camera.
    Returns (yaw_deg, pitch_deg, per_point_errors).
    """
    cam = np.array(cam_pos_ft, float)
    fx, cx = K[0,0], K[0,2]
    fy, cy = K[1,1], K[1,2]
    yaw_est, pitch_est = [], []
    for p3, uv in zip(pts3d_ft, uv_px):
        d = np.array(p3, float) - cam
        # true azimuth: angle in XZ plane, 0 = +Z (south), positive toward +X (east)
        az_true = np.degrees(np.arctan2(d[0], d[2]))       # east(+)/south
        # true elevation: angle above horizontal (positive up)
        horiz = np.hypot(d[0], d[2])
        el_true = np.degrees(np.arctan2(d[1], horiz))      # up positive
        # pixel-derived angles (camera frame)
        pan_px = np.degrees(np.arctan2(uv[0]-cx, fx))      # + => right in image
        tilt_px = np.degrees(np.arctan2(uv[1]-cy, fy))     # + => down in image
        # yaw = azimuth camera looks toward (0=south +Z, + = east +X)
        #   point azimuth az_true appears at pan_px => az_true = yaw + pan_px
        # pitch = elevation of optical axis (positive up)
        #   point elevation el_true appears at tilt_px => tilt_px = pitch - el_true
        yaw_est.append(az_true - pan_px)
        pitch_est.append(el_true + tilt_px)
    yaw = float(np.mean(yaw_est))
    pitch = float(np.mean(pitch_est))
    errs = {'yaw_spread': float(np.std(yaw_est)), 'pitch_spread': float(np.std(pitch_est))}
    return yaw, pitch, errs

def estimate_pose_pnp(cam_pos_ft, pts3d_ft, uv_px, K, dist=None):
    """Full 6DOF pose via solvePnP (needs >=4 correspondences)."""
    obj = np.array([[p[0], p[1], p[2]] for p in pts3d_ft], float)
    img = np.array(uv_px, float).reshape(-1,1,2)
    if dist is None:
        dist = np.zeros(5)
    ok, rvec, tvec = cv2.solvePnP(obj, img, K, dist)
    R, _ = cv2.Rodrigues(rvec)
    return ok, R, tvec.ravel()

if __name__ == '__main__':
    # Quick PTZ pan/tilt inference using the two junction poles detected at x=402,456
    cam_pos = (12.375, 5.0, 8.82)
    pts3d = [
        (12.011, 3.05, 7.32),   # 2x5 NE pole (approx pole center height y=3.05)
        (12.156, 3.05, 7.32),   # 3x6 NW pole
    ]
    uv = [(402, 375), (456, 375)]
    K = np.array([[900, 0, 640], [0, 900, 360], [0, 0, 1]], float)
    yaw, pitch, errs = infer_yaw_pitch(cam_pos, pts3d, uv, K, (1280,720))
    print(f'PTZ inferred yaw={yaw:.1f}deg  pitch={pitch:.1f}deg  (spread yaw={errs["yaw_spread"]:.1f}, pitch={errs["pitch_spread"]:.1f})')
    # back-check: project with inferred yaw/pitch
    cam = Camera('ptz', cam_pos, yaw_deg=yaw, pitch_deg=pitch, K=K)
    for p3 in pts3d:
        print('  project', p3, '->', cam.project(p3))
