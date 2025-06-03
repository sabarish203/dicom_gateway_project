from pydicom.dataset import Dataset, FileDataset
from datetime import datetime
import os

filename = "sample.dcm"
file_meta = Dataset()
file_meta.MediaStorageSOPClassUID = "1.2.840.10008.5.1.4.1.1.2"  # CTImageStorage
file_meta.MediaStorageSOPInstanceUID = "1.2.826.0.1.3680043.2.1125.1.1"
file_meta.ImplementationClassUID = "1.2.3.4"

ds = FileDataset(filename, {}, file_meta=file_meta, preamble=b"\0" * 128)
ds.PatientName = "Test^Patient"
ds.PatientID = "123456"
ds.StudyInstanceUID = "1.2.3.4.5.6.7.8.1"
ds.SeriesInstanceUID = "1.2.3.4.5.6.7.8.2"
ds.SOPInstanceUID = "1.2.3.4.5.6.7.8.3"
ds.Modality = "CT"
ds.StudyDate = datetime.now().strftime('%Y%m%d')
ds.StudyTime = datetime.now().strftime('%H%M%S')
ds.Rows = 2
ds.Columns = 2
ds.BitsAllocated = 16
ds.PixelData = b'\x00\x01\x00\x02\x00\x03\x00\x04'

ds.save_as(filename)
print(f"Sample DICOM saved as {filename}")
