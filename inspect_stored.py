import os
from pydicom import dcmread

def inspect_storage():
    storage_path = os.path.join('dicom_listener', 'buffer')
    if not os.path.exists(storage_path):
        print("No DICOM files stored yet")
        return

    print(f"Checking storage at: {os.path.abspath(storage_path)}")
    count = 0
    
    for root, _, files in os.walk(storage_path):
        for file in files:
            if file.endswith('.dcm'):
                path = os.path.join(root, file)
                try:
                    # Add force=True to read incomplete DICOM files
                    ds = dcmread(path, force=True)
                    print(f"\n[{count+1}] File: {path}")
                    print(f"   Patient: {ds.get('PatientName', 'UNKNOWN')}")
                    print(f"   Study UID: {ds.get('StudyInstanceUID', 'UNKNOWN')}")
                    print(f"   Series UID: {ds.get('SeriesInstanceUID', 'UNKNOWN')}")
                    print(f"   SOP Instance UID: {ds.get('SOPInstanceUID', 'UNKNOWN')}")
                    print(f"   Modality: {ds.get('Modality', 'UNKNOWN')}")
                    count += 1
                except Exception as e:
                    print(f"Error reading {path}: {str(e)}")

    print(f"\nFound {count} DICOM file(s)")

if __name__ == "__main__":
    inspect_storage()