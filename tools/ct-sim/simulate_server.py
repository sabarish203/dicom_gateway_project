import os
import time
from pydicom import dcmread
from pynetdicom import AE, build_context
from pynetdicom.sop_class import CTImageStorage
from pydicom.uid import ExplicitVRLittleEndian, generate_uid

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DICOM_FOLDER = os.path.join(SCRIPT_DIR, "datasets", "chest")

GATEWAY_HOST = "localhost"
GATEWAY_PORT = 11112
AE_TITLE = "CT-SIM"
TLS_ENABLED = os.getenv("TLS_ENABLED", "false").lower() == "true"

def send_ct_study():
    ae = AE(ae_title=AE_TITLE)
    ae.requested_contexts = [build_context(CTImageStorage)]

    tls_args = None
    if TLS_ENABLED:
        import ssl
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE
        tls_args = (ssl_ctx, "localhost")

    assoc = ae.associate(GATEWAY_HOST, GATEWAY_PORT, ae_title="ANY-SCP", tls_args=tls_args)

    if not assoc.is_established:
        print("Association failed.")
        return

    for filename in sorted(os.listdir(DICOM_FOLDER)):
        if not filename.endswith(".dcm"):
            continue
        filepath = os.path.join(DICOM_FOLDER, filename)
        ds = dcmread(filepath)

        ds.SOPClassUID = CTImageStorage
        ds.SOPInstanceUID = generate_uid()
        ds.file_meta = ds.file_meta or {}
        ds.file_meta.TransferSyntaxUID = ExplicitVRLittleEndian

        status = assoc.send_c_store(ds)
        print(f"Sent {filename}: Status 0x{status.Status:04X}")
        time.sleep(0.2)

    assoc.release()

if __name__ == "__main__":
    send_ct_study()
