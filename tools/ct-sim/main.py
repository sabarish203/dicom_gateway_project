import argparse
from pynetdicom import AE, evt
from pydicom import dcmread
import os
import threading

def send_slices(args):
    ae = AE(ae_title=args.gateway_ae)
    ae.add_requested_context('1.2.840.10008.5.1.4.1.1.2')  # CT Storage
    for fname in os.listdir(args.src):
        if not fname.endswith('.dcm'): continue
        ds = dcmread(os.path.join(args.src, fname))
        assoc = ae.associate(args.gateway_host, args.gateway_port)
        if assoc.is_established:
            assoc.send_c_store(ds)
            assoc.release()

def handle_echo(event):
    return 0x0000  # Success

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--src', default='/sim/datasets/chest')
    parser.add_argument('--listen-port', type=int, default=105)
    parser.add_argument('--gateway-ae', default='PY_GATEWAY')
    parser.add_argument('--gateway-host', default='dicom-gw')
    parser.add_argument('--gateway-port', type=int, default=104)
    args = parser.parse_args()

    # Start SCP
    ae = AE(ae_title='CT_SIM')
    ae.add_supported_context('1.2.840.10008.5.1.4.1.1.2')
    ae.add_handler(evt.EVT_C_ECHO, handle_echo)
    
    # Start SCU in background
    threading.Thread(target=send_slices, args=(args,), daemon=True).start()
    
    ae.start_server(('0.0.0.0', args.listen_port), block=True)