# camera-whep: a SpiriSynq camera served as WHEP, for cloud-link's mediamtx.
# SpiriCamera's image, with camera_whep.py as its entrypoint.
FROM ghcr.io/spiri-robotics/spiricamera:edge
COPY camera_whep.py /opt/camera-whep/camera_whep.py
ENTRYPOINT ["python", "/opt/camera-whep/camera_whep.py"]
