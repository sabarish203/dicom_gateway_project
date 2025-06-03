from pydicom import Dataset, dcmwrite
from pydicom.uid import generate_uid, ImplicitVRLittleEndian
import os

def create_test_dicom():
    ds = Dataset()
    
    # File Meta Information
    ds.file_meta = Dataset()
    ds.file_meta.TransferSyntaxUID = ImplicitVRLittleEndian
    ds.file_meta.MediaStorageSOPClassUID = "1.2.840.10008.5.1.4.1.1.2"  # CT
    ds.file_meta.MediaStorageSOPInstanceUID = generate_uid()
    ds.file_meta.ImplementationClassUID = generate_uid()
    
    # Main Dataset
    ds.PatientName = "Test^Patient"
    ds.PatientID = "12345"
    ds.StudyInstanceUID = generate_uid()
    ds.SeriesInstanceUID = generate_uid()
    ds.SOPInstanceUID = ds.file_meta.MediaStorageSOPInstanceUID
    ds.Modality = "CT"
    ds.Rows = 256
    ds.Columns = 256
    ds.PixelData = bytes(256*256)  # Blank image
    
    # Required CT attributes
    ds.BitsAllocated = 16
    ds.BitsStored = 16
    ds.HighBit = 15
    ds.PixelRepresentation = 0
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = "MONOCHROME2"

    os.makedirs("test_data", exist_ok=True)
    ds.save_as("test_data/valid_ct.dcm", write_like_original=False)

if __name__ == "__main__":
    create_test_dicom()
    print("Created valid DICOM CT file at:", os.path.abspath("test_data/valid_ct.dcm"))