import os
import ssl
import time
import pytest
from pynetdicom import AE, evt, build_context
from pynetdicom.sop_class import Verification, CTImageStorage
from pydicom import dcmread
from pydicom.uid import generate_uid, ExplicitVRLittleEndian
from pydicom.dataset import FileMetaDataset

# Paths
TLS_CERT = "certs/server.crt"
TLS_KEY = "certs/server.key"
SAMPLE_DCM = "sample.dcm"

@pytest.fixture(scope="module", autouse=True)
def wait_for_listener():
    """Allow listener time to start"""
    time.sleep(1)

def test_echo_over_tls():
    ae = AE()
    ae.requested_contexts = [build_context(Verification)]

    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    assoc = ae.associate("localhost", 11112, ae_title="ANY-SCP", tls_args=(ssl_context, "localhost"))
    assert assoc.is_established, "Association failed"
    assoc.release()

def test_store_ct_image_tls():
    ae = AE()
    ae.requested_contexts = [build_context(CTImageStorage)]

    ds = dcmread(SAMPLE_DCM)

    # Inject required DICOM metadata
    ds.SOPClassUID = str(CTImageStorage)
    ds.SOPInstanceUID = generate_uid()

    ds.file_meta = FileMetaDataset()
    ds.file_meta.MediaStorageSOPClassUID = str(CTImageStorage)
    ds.file_meta.MediaStorageSOPInstanceUID = ds.SOPInstanceUID
    ds.file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    ds.file_meta.ImplementationClassUID = generate_uid()

    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    assoc = ae.associate("localhost", 11112, ae_title="ANY-SCP", tls_args=(ssl_context, "localhost"))
    assert assoc.is_established, "Association failed"

    status = assoc.send_c_store(ds)
    assert status.Status == 0x0000, f"C-STORE failed with status: {status!r}"
    assoc.release()
