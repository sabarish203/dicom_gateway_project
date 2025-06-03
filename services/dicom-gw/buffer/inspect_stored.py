import os
BUFFER_DIR = "buffer"
for root, _, files in os.walk(BUFFER_DIR):
    for file in files:
        if file.endswith(".dcm"):
            print("Found:", os.path.join(root, file))