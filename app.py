from flask import Flask, render_template, request
import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import RoundedModuleDrawer
from PIL import Image
import io
import base64
import os
from dotenv import load_dotenv
from bakong_khqr import KHQR

# Get the absolute path of the current file's directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)

# Load environment variables
load_dotenv()

# Get token from environment variable
BAKONG_TOKEN = os.getenv("BAKONG_TOKEN")
if not BAKONG_TOKEN:
    raise ValueError("BAKONG_TOKEN is not set in environment variables")

# Create a new KHQR object
khqr = KHQR(BAKONG_TOKEN)

def generate_qr_with_logo(qr_data):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)

    # Create QR code image
    qr_image = qr.make_image(
        fill_color="black", 
        back_color="white", 
        image_factory=StyledPilImage, 
        module_drawer=RoundedModuleDrawer()
    )
    
    # Convert to RGB mode if it isn't already
    if qr_image.mode != 'RGB':
        qr_image = qr_image.convert('RGB')

    # Open the logo image using absolute path
    logo_path = os.path.join(BASE_DIR, "bakong_khqr", "static", "logo.jpg")
    try:
        logo = Image.open(logo_path)
        # Convert logo to RGB mode
        if logo.mode != 'RGB':
            logo = logo.convert('RGB')
            
        # Calculate the size of the logo (20% of the QR code size)
        logo_size = int(qr_image.size[0] * 0.2)
        logo = logo.resize((logo_size, logo_size))

        # Create a white background square for the logo
        white_square = Image.new('RGB', (logo_size, logo_size), 'white')
        
        # Calculate position to paste
        pos = ((qr_image.size[0] - logo_size) // 2, 
               (qr_image.size[1] - logo_size) // 2)
        
        # First paste the white square
        qr_image.paste(white_square, pos)
        # Then paste the logo
        qr_image.paste(logo, pos)

    except Exception as e:
        print(f"Error processing logo: {str(e)}")
        # Continue without logo if there's an error

    # Save QR code to a bytes buffer
    buffer = io.BytesIO()
    qr_image.save(buffer, format="PNG")
    qr_image_base64 = base64.b64encode(buffer.getvalue()).decode()

    return qr_image_base64

@app.route('/', methods=['GET', 'POST'])
def index():
    qr_image = None
    amount = ""
    if request.method == 'POST':
        amount = request.form.get('amount', '')
        if amount:
            try:
                # Create QR code
                qr_data = khqr.create_qr(
                    bank_account="proeung_chiso@aclb",
                    merchant_city="Phnom Penh",
                    merchant_name="Cloudidator Co., Ltd.",
                    amount=float(amount),
                    currency="KHR",
                    store_label="My Store",
                    phone_number="855967920804",
                    bill_number="TRX123456",
                    terminal_label="POS-01",
                    static=False
                )
                qr_image = generate_qr_with_logo(qr_data)
            except Exception as e:
                print(f"Error generating QR code: {str(e)}")
                qr_image = None

    return render_template('qr.html', qr_image=qr_image, amount=amount)

if __name__ == '__main__':
    app.run(debug=True)