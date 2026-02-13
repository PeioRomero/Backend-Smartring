from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import stripe
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from datetime import datetime
import secrets

# Flask app configuration
app = Flask(__name__)
CORS(app)

# Stripe configuration
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY', 'sk_test_YOUR_KEY_HERE')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', 'whsec_YOUR_WEBHOOK_SECRET')

# Email configuration
SUPPLIER_EMAIL = os.environ.get('SUPPLIER_EMAIL', 'your_email@gmail.com')
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_EMAIL = os.environ.get('SMTP_EMAIL', 'your_email@gmail.com')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', 'your_app_password')

# Database setup
DATABASE = 'dropshipping.db'

def init_db():
    """Initialize the database"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_number TEXT UNIQUE NOT NULL,
            customer_name TEXT NOT NULL,
            customer_email TEXT NOT NULL,
            customer_phone TEXT,
            shipping_address TEXT NOT NULL,
            shipping_city TEXT NOT NULL,
            shipping_postal_code TEXT NOT NULL,
            shipping_country TEXT NOT NULL,
            ring_size TEXT NOT NULL,
            ring_color TEXT NOT NULL,
            product_name TEXT DEFAULT 'SmartRing Pro',
            quantity INTEGER DEFAULT 1,
            total_amount REAL NOT NULL,
            stripe_payment_id TEXT,
            supplier_notified BOOLEAN DEFAULT 0,
            order_status TEXT DEFAULT 'processing',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("Database initialized successfully")

def generate_order_number():
    """Generate a unique order number"""
    timestamp = datetime.now().strftime('%Y%m%d')
    random_part = secrets.token_hex(4).upper()
    return f"SR-{timestamp}-{random_part}"

def send_email(to_email, subject, body):
    """Send email using SMTP"""
    try:
        msg = MIMEMultipart()
        msg['From'] = SMTP_EMAIL
        msg['To'] = to_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'html'))
        
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_EMAIL, SMTP_PASSWORD)
        text = msg.as_string()
        server.sendmail(SMTP_EMAIL, to_email, text)
        server.quit()
        
        print(f"Email sent successfully to {to_email}")
        return True
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        return False

def send_customer_confirmation(order_data):
    """Send order confirmation to customer"""
    subject = f"Confirmación de Pedido - {order_data['order_number']}"
    
    body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: linear-gradient(135deg, #6366f1, #8b5cf6); padding: 30px; text-align: center;">
            <h1 style="color: white; margin: 0;">¡Pedido Confirmado!</h1>
        </div>
        
        <div style="padding: 30px; background: #f9fafb;">
            <h2 style="color: #1f2937;">Gracias por tu compra, {order_data['customer_name']}!</h2>
            
            <p style="font-size: 16px; color: #6b7280;">
                Tu pedido ha sido confirmado y será procesado en breve.
            </p>
            
            <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3 style="color: #6366f1;">Detalles del Pedido</h3>
                <p><strong>Número de Pedido:</strong> {order_data['order_number']}</p>
                <p><strong>Producto:</strong> SmartRing Pro</p>
                <p><strong>Talla:</strong> {order_data['ring_size']}</p>
                <p><strong>Color:</strong> {order_data['ring_color']}</p>
                <p><strong>Total:</strong> €29.99</p>
            </div>
            
            <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3 style="color: #6366f1;">Dirección de Envío</h3>
                <p>{order_data['shipping_address']}</p>
                <p>{order_data['shipping_city']}, {order_data['shipping_postal_code']}</p>
                <p>{order_data['shipping_country']}</p>
            </div>
            
            <p style="font-size: 14px; color: #9ca3af; margin-top: 30px;">
                Recibirás un email con el número de seguimiento cuando tu pedido sea enviado.
            </p>
        </div>
        
        <div style="background: #1f2937; padding: 20px; text-align: center; color: white;">
            <p style="margin: 0;">SmartRing Pro - Tu salud en tus manos</p>
        </div>
    </body>
    </html>
    """
    
    return send_email(order_data['customer_email'], subject, body)

def send_supplier_notification(order_data):
    """Send order notification to supplier (your email)"""
    subject = f"🛒 NUEVO PEDIDO - {order_data['order_number']}"
    
    # AliExpress product URL
    aliexpress_url = "https://es.aliexpress.com/item/1005008785029922.html"
    
    body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: #dc2626; padding: 30px; text-align: center;">
            <h1 style="color: white; margin: 0;">⚡ NUEVO PEDIDO RECIBIDO</h1>
        </div>
        
        <div style="padding: 30px; background: #f9fafb;">
            <h2 style="color: #1f2937;">Acción: Comprar en AliExpress</h2>
            
            <!-- Quick Action Button -->
            <div style="text-align: center; margin: 30px 0;">
                <a href="{aliexpress_url}" 
                   style="background: linear-gradient(135deg, #FF6A00, #EE4D2D); 
                          color: white; 
                          padding: 15px 40px; 
                          text-decoration: none; 
                          border-radius: 8px; 
                          font-size: 18px; 
                          font-weight: bold;
                          display: inline-block;">
                    🛒 COMPRAR EN ALIEXPRESS
                </a>
            </div>
            
            <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #dc2626;">
                <h3 style="color: #dc2626;">Información del Producto</h3>
                <p><strong>Producto:</strong> SmartRing Pro</p>
                <p><strong>Talla:</strong> {order_data['ring_size']}</p>
                <p><strong>Color:</strong> {order_data['ring_color']}</p>
                <p><strong>Cantidad:</strong> 1 unidad</p>
                <p><strong>Enlace:</strong> <a href="{aliexpress_url}" target="_blank">Abrir en AliExpress</a></p>
            </div>
            
            <div style="background: #fff3cd; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #f59e0b;">
                <h3 style="color: #f59e0b; margin-top: 0;">📋 DATOS PARA COPIAR EN ALIEXPRESS</h3>
                
                <div style="background: white; padding: 15px; border-radius: 5px; margin: 10px 0; font-family: monospace;">
                    <p style="margin: 5px 0;"><strong>Nombre:</strong></p>
                    <p style="margin: 5px 0; padding: 8px; background: #f3f4f6; border-radius: 4px;">{order_data['customer_name']}</p>
                    
                    <p style="margin: 5px 0;"><strong>Teléfono:</strong></p>
                    <p style="margin: 5px 0; padding: 8px; background: #f3f4f6; border-radius: 4px;">{order_data['customer_phone']}</p>
                    
                    <p style="margin: 5px 0;"><strong>Dirección:</strong></p>
                    <p style="margin: 5px 0; padding: 8px; background: #f3f4f6; border-radius: 4px;">{order_data['shipping_address']}</p>
                    
                    <p style="margin: 5px 0;"><strong>Ciudad:</strong></p>
                    <p style="margin: 5px 0; padding: 8px; background: #f3f4f6; border-radius: 4px;">{order_data['shipping_city']}</p>
                    
                    <p style="margin: 5px 0;"><strong>Código Postal:</strong></p>
                    <p style="margin: 5px 0; padding: 8px; background: #f3f4f6; border-radius: 4px;">{order_data['shipping_postal_code']}</p>
                    
                    <p style="margin: 5px 0;"><strong>País:</strong></p>
                    <p style="margin: 5px 0; padding: 8px; background: #f3f4f6; border-radius: 4px;">{order_data['shipping_country']}</p>
                </div>
            </div>
            
            <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3 style="color: #6366f1;">Información del Cliente</h3>
                <p><strong>Email del Cliente:</strong> {order_data['customer_email']}</p>
            </div>
            
            <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3 style="color: #6366f1;">Detalles del Pedido</h3>
                <p><strong>Número de Pedido:</strong> {order_data['order_number']}</p>
                <p><strong>ID de Pago Stripe:</strong> {order_data['stripe_payment_id']}</p>
                <p><strong>Fecha:</strong> {order_data['created_at']}</p>
            </div>
            
            <div style="background: #fef3c7; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #f59e0b;">
                <h3 style="color: #f59e0b; margin-top: 0;">⚠️ PASOS A SEGUIR</h3>
                <ol style="margin: 10px 0; padding-left: 20px;">
                    <li>Click en "COMPRAR EN ALIEXPRESS" arriba</li>
                    <li>Selecciona la talla: <strong>{order_data['ring_size']}</strong> y color: <strong>{order_data['ring_color']}</strong></li>
                    <li>Copia los datos de envío del recuadro amarillo</li>
                    <li>Completa la compra en AliExpress</li>
                    <li>Guarda el número de tracking cuando llegue</li>
                </ol>
            </div>
        </div>
        
        <div style="background: #1f2937; padding: 20px; text-align: center; color: white;">
            <p style="margin: 0;">Sistema de Dropshipping Automático</p>
            <p style="margin: 5px 0; font-size: 12px;">Pago ya recibido y confirmado ✅</p>
        </div>
    </body>
    </html>
    """
    
    return send_email(SUPPLIER_EMAIL, subject, body)

@app.route('/api/create-payment-intent', methods=['POST'])
def create_payment_intent():
    """Create a payment intent with Stripe"""
    try:
        data = request.json
        
        # Generate order number
        order_number = generate_order_number()
        
        # Create payment intent
        intent = stripe.PaymentIntent.create(
            amount=data['amount'],  # Amount in cents
            currency='eur',
            metadata={
                'order_number': order_number,
                'customer_name': data['name'],
                'customer_email': data['email'],
                'customer_phone': data.get('phone', ''),
                'shipping_address': data['address'],
                'shipping_city': data['city'],
                'shipping_postal': data['postal'],
                'shipping_country': data['country'],
                'ring_size': data['size'],
                'ring_color': data['color']
            }
        )
        
        # Save order to database (pending payment)
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO orders (
                order_number, customer_name, customer_email, customer_phone,
                shipping_address, shipping_city, shipping_postal_code, shipping_country,
                ring_size, ring_color, total_amount, stripe_payment_id, order_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            order_number,
            data['name'],
            data['email'],
            data.get('phone', ''),
            data['address'],
            data['city'],
            data['postal'],
            data['country'],
            data['size'],
            data['color'],
            data['amount'] / 100,  # Convert cents to euros
            intent.id,
            'pending_payment'
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'clientSecret': intent.client_secret,
            'orderId': order_number
        })
        
    except Exception as e:
        print(f"Error creating payment intent: {str(e)}")
        return jsonify({'error': str(e)}), 400

@app.route('/api/webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhook events"""
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError as e:
        return jsonify({'error': 'Invalid signature'}), 400
    
    # Handle successful payment
    if event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        
        # Update order status
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE orders 
            SET order_status = 'paid'
            WHERE stripe_payment_id = ?
        ''', (payment_intent.id,))
        
        conn.commit()
        
        # Get order details
        cursor.execute('''
            SELECT * FROM orders WHERE stripe_payment_id = ?
        ''', (payment_intent.id,))
        
        order = cursor.fetchone()
        conn.close()
        
        if order:
            # Prepare order data
            order_data = {
                'order_number': order[1],
                'customer_name': order[2],
                'customer_email': order[3],
                'customer_phone': order[4],
                'shipping_address': order[5],
                'shipping_city': order[6],
                'shipping_postal_code': order[7],
                'shipping_country': order[8],
                'ring_size': order[9],
                'ring_color': order[10],
                'stripe_payment_id': order[14],
                'created_at': order[17]
            }
            
            # Send confirmation to customer
            send_customer_confirmation(order_data)
            
            # Send notification to supplier (your email)
            supplier_notified = send_supplier_notification(order_data)
            
            # Update supplier notification status
            if supplier_notified:
                conn = sqlite3.connect(DATABASE)
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE orders 
                    SET supplier_notified = 1, order_status = 'processing'
                    WHERE stripe_payment_id = ?
                ''', (payment_intent.id,))
                conn.commit()
                conn.close()
    
    return jsonify({'status': 'success'})

@app.route('/api/orders/<order_id>', methods=['GET'])
def get_order(order_id):
    """Get order details"""
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM orders WHERE order_number = ?', (order_id,))
        order = cursor.fetchone()
        conn.close()
        
        if order:
            return jsonify({
                'order_number': order[1],
                'customer_name': order[2],
                'customer_email': order[3],
                'status': order[15],
                'created_at': order[16]
            })
        else:
            return jsonify({'error': 'Order not found'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/admin/orders', methods=['GET'])
def get_all_orders():
    """Get all orders (admin endpoint)"""
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM orders ORDER BY created_at DESC')
        orders = cursor.fetchall()
        conn.close()
        
        orders_list = []
        for order in orders:
            orders_list.append({
                'id': order[0],
                'order_number': order[1],
                'customer_name': order[2],
                'customer_email': order[3],
                'total': order[12],
                'status': order[15],
                'supplier_notified': bool(order[14]),
                'created_at': order[16]
            })
        
        return jsonify({'orders': orders_list})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'message': 'Server is running'})

# Initialize database when app starts (works with Gunicorn)
init_db()

if __name__ == '__main__':
    # Run server locally
    print("Starting Dropshipping Backend Server...")
    print("Supplier email:", SUPPLIER_EMAIL)
    print("Stripe configured")
    print("\nIMPORTANT: Server is running on http://localhost:5000")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
