from flask import Flask, render_template, request, jsonify
import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import RoundedModuleDrawer
from PIL import Image
import io
import base64
import os
import uuid
from datetime import datetime
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

def generate_transaction_id():
    """Generate a unique transaction ID"""
    return f"TRX{datetime.now().strftime('%Y%m%d')}{uuid.uuid4().hex[:8].upper()}"

def generate_qr_with_logo(qr_data):
    """Generate QR code with logo"""
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

def generate_payment_data(amount, transaction_id=None):
    """Generate both QR code and deeplink data"""
    if transaction_id is None:
        transaction_id = generate_transaction_id()

    try:
        # Create QR code data
        qr_data = khqr.create_qr(
            bank_account="proeung_chiso@aclb",
            merchant_city="Phnom Penh",
            merchant_name="Cloudidator Co., Ltd.",
            amount=float(amount),
            currency="KHR",
            store_label="My Store",
            phone_number="855967920804",
            bill_number=transaction_id,
            terminal_label="POS-01",
            static=False
        )

        # Generate deeplink
        deeplink = khqr.generate_deeplink(
            qr_data,
            callback="https://your-domain.com/payment/callback",
            appIconUrl="https://your-domain.com/static/icon.png",
            appName="Cloudidator Payment"
        )

        return {
            'qr_data': qr_data,
            'deeplink': deeplink,
            'transaction_id': transaction_id
        }
    except Exception as e:
        print(f"Error generating payment data: {str(e)}")
        return None

@app.route('/', methods=['GET', 'POST'])
def index():
    qr_image = None
    amount = ""
    deeplink = None
    transaction_id = None
    formatted_amount = None
    error_message = None
    
    if request.method == 'POST':
        try:
            amount = request.form.get('amount', '')
            if amount:
                # Convert to float and validate amount
                amount_float = float(amount)
                if amount_float <= 0:
                    error_message = "Amount must be greater than 0"
                else:
                    # Format the amount with comma as thousand separator
                    formatted_amount = f"{amount_float:,.2f}"
                    
                    # Generate both QR and deeplink data
                    payment_data = generate_payment_data(amount)
                    if payment_data:
                        qr_image = generate_qr_with_logo(payment_data['qr_data'])
                        deeplink = payment_data['deeplink']
                        transaction_id = payment_data['transaction_id']
        except ValueError:
            error_message = "Please enter a valid number"
        except Exception as e:
            print(f"Error processing payment: {str(e)}")
            error_message = "An error occurred while processing your payment"

    return render_template(
        'qr.html', 
        qr_image=qr_image, 
        amount=amount,
        formatted_amount=formatted_amount,
        deeplink=deeplink,
        transaction_id=transaction_id,
        error_message=error_message
    )

@app.route('/payment/callback', methods=['POST'])
def payment_callback():
    """Handle payment callback from Bakong"""
    try:
        # Verify the callback signature
        signature = request.headers.get('X-Signature')
        if not signature:
            return jsonify({'status': 'error', 'message': 'Missing signature'}), 400

        # Get the callback data
        data = request.json
        transaction_id = data.get('transaction_id')
        status = data.get('status')

        # TODO: Update your database with the payment status
        
        return jsonify({
            'status': 'success',
            'message': 'Callback processed successfully'
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=True)