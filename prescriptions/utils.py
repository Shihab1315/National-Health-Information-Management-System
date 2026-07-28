import qrcode
from io import BytesIO
from django.core.files import File
from django.conf import settings
import os

def generate_prescription_qr(prescription):
    """Generate QR code for prescription and save to model."""
    if prescription.qr_code:
        return prescription.qr_code

    # Data to encode: prescription number + patient + doctor
    data = f"RX:{prescription.prescription_number}|PAT:{prescription.patient.id}|DOC:{prescription.doctor.id}"
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill='black', back_color='white')

    # Save to BytesIO
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    filename = f"qr_{prescription.prescription_number}.png"
    path = os.path.join('prescriptions/qr/', filename)

    # Save to model
    prescription.qr_code.save(filename, File(buffer), save=False)
    prescription.save(update_fields=['qr_code'])
    return prescription.qr_code