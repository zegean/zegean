from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
from datetime import datetime
import uuid

app = Flask(__name__)
app.secret_key = 'emin123_ticaret_sitesi_gelismis'
app.config['DATABASE'] = 'eticaret_gelismis.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Upload klasörünü oluştur
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

def get_db_connection():
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    
    # Kullanıcılar
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            full_name TEXT,
            is_admin BOOLEAN DEFAULT FALSE
        )
    ''')
    
    # Kategoriler
    conn.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT
        )
    ''')
    
    # Ürünler
    conn.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            category_id INTEGER,
            image_url TEXT,
            stock INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Sepet
    conn.execute('''
        CREATE TABLE IF NOT EXISTS cart (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            product_id INTEGER,
            quantity INTEGER DEFAULT 1
        )
    ''')
    
    # Siparişler
    conn.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            total_amount REAL,
            status TEXT DEFAULT 'pending',
            customer_name TEXT,
            customer_email TEXT,
            customer_phone TEXT,
            customer_address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Sipariş ürünleri
    conn.execute('''
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            product_id INTEGER,
            product_name TEXT,
            product_image TEXT,
            quantity INTEGER,
            price REAL
        )
    ''')
    
    # Admin kullanıcısı
    admin_user = conn.execute('SELECT * FROM users WHERE email = ?', ('emin123@gmail.com',)).fetchone()
    if not admin_user:
        admin_password = generate_password_hash('11223344')
        conn.execute('INSERT INTO users (email, password, full_name, is_admin) VALUES (?, ?, ?, ?)',
                    ('emin123@gmail.com', admin_password, 'Admin User', True))
        print("✅ Admin kullanıcısı eklendi!")
    
    # Kategoriler
    categories_count = conn.execute('SELECT COUNT(*) as count FROM categories').fetchone()['count']
    if categories_count == 0:
        categories = [
            ('Zeytinyağı', 'Premium zeytinyağları'),
            ('Zeytin', 'Çeşit çeşit zeytinler'),
            ('Yöresel Lezzetler', 'Yöresel ürünler'),
            ('Kişisel Bakım', 'Doğal bakım ürünleri'),
            ('Sağlık Ürünleri', 'Sağlıklı yaşam ürünleri'),
            ('Bahçe Ürünleri', 'Bahçe ürünleri')
        ]
        conn.executemany('INSERT INTO categories (name, description) VALUES (?, ?)', categories)
        print("✅ Kategoriler eklendi!")
    
    # Örnek ürünler
    products_count = conn.execute('SELECT COUNT(*) as count FROM products').fetchone()['count']
    if products_count == 0:
        products = [
            ('Naturel Sızma Zeytinyağı', 'Soğuk sıkım naturel zeytinyağı', 125.90, 1, 'https://images.unsplash.com/photo-1631570622572-02cace4b1531?w=400', 50),
            ('Erken Hasat Zeytinyağı', 'Erken hasat premium zeytinyağı', 145.50, 1, 'https://images.unsplash.com/photo-1586769852836-bc069f19e1b6?w=400', 30),
            ('Organik Yeşil Zeytin', 'Organik yeşil zeytin', 45.50, 2, 'https://images.unsplash.com/photo-1611854778586-e81143a47665?w=400', 100),
            ('Siyah Zeytin', 'Doğal siyah zeytin', 35.00, 2, 'https://images.unsplash.com/photo-1574323347407-f5e1ad6d020b?w=400', 80),
            ('Köy Peyniri', 'Geleneksel köy peyniri', 85.00, 3, 'https://images.unsplash.com/photo-1565299624946-b28f40a0ca4b?w=400', 30),
            ('Zeytinyağlı Sabun', 'Doğal zeytinyağlı sabun', 25.00, 4, 'https://images.unsplash.com/photo-1600857062244-5c0071b5d6c1?w=400', 75)
        ]
        conn.executemany('INSERT INTO products (name, description, price, category_id, image_url, stock) VALUES (?, ?, ?, ?, ?, ?)', products)
        print("✅ Örnek ürünler eklendi!")
    
    conn.commit()
    conn.close()
    print("🎉 Veritabanı hazır!")

def get_cart_count(user_id):
    try:
        conn = get_db_connection()
        count = conn.execute('SELECT SUM(quantity) as total FROM cart WHERE user_id = ?', (user_id,)).fetchone()['total']
        conn.close()
        return count or 0
    except:
        return 0

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_image(file):
    if file and allowed_file(file.filename):
        file_extension = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4().hex}.{file_extension}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        return f"/static/uploads/{filename}"
    return None

# Ana Sayfa
@app.route('/')
def index():
    conn = get_db_connection()
    products = conn.execute('SELECT * FROM products LIMIT 8').fetchall()
    categories = conn.execute('SELECT * FROM categories').fetchall()
    conn.close()
    
    cart_count = get_cart_count(session.get('user_id', 0))
    
    return render_template('index.html', products=products, categories=categories, cart_count=cart_count)

# Arama
@app.route('/search')
def search():
    query = request.args.get('q', '')
    conn = get_db_connection()
    
    if query:
        products = conn.execute('SELECT * FROM products WHERE name LIKE ? OR description LIKE ?', (f'%{query}%', f'%{query}%')).fetchall()
    else:
        products = conn.execute('SELECT * FROM products LIMIT 8').fetchall()
    
    categories = conn.execute('SELECT * FROM categories').fetchall()
    conn.close()
    
    cart_count = get_cart_count(session.get('user_id', 0))
    
    return render_template('index.html', products=products, categories=categories, search_query=query, cart_count=cart_count)

# Giriş
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['user_email'] = user['email']
            session['user_name'] = user['full_name']
            session['is_admin'] = user['is_admin']
            flash('Başarıyla giriş yapıldı!', 'success')
            return redirect(url_for('index'))
        else:
            flash('E-posta veya şifre hatalı!', 'error')
    
    return render_template('login.html')

# Kayıt
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        full_name = request.form['full_name']
        
        if password != confirm_password:
            flash('Şifreler eşleşmiyor!', 'error')
            return render_template('register.html')
        
        conn = get_db_connection()
        existing_user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        
        if existing_user:
            flash('Bu e-posta zaten kullanılıyor!', 'error')
            conn.close()
            return render_template('register.html')
        
        hashed_password = generate_password_hash(password)
        conn.execute('INSERT INTO users (email, password, full_name) VALUES (?, ?, ?)', (email, hashed_password, full_name))
        conn.commit()
        conn.close()
        
        flash('Kayıt başarılı! Giriş yapabilirsiniz.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

# Çıkış
@app.route('/logout')
def logout():
    session.clear()
    flash('Çıkış yapıldı!', 'info')
    return redirect(url_for('index'))

# Kategori
@app.route('/category/<int:category_id>')
def category(category_id):
    conn = get_db_connection()
    category = conn.execute('SELECT * FROM categories WHERE id = ?', (category_id,)).fetchone()
    products = conn.execute('SELECT * FROM products WHERE category_id = ?', (category_id,)).fetchall()
    categories = conn.execute('SELECT * FROM categories').fetchall()
    conn.close()
    
    cart_count = get_cart_count(session.get('user_id', 0))
    
    return render_template('category.html', category=category, products=products, categories=categories, cart_count=cart_count)

# Sepet
@app.route('/cart')
def cart():
    if 'user_id' not in session:
        flash('Sepeti görüntülemek için giriş yapın!', 'error')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cart_items = conn.execute('''
        SELECT cart.*, products.name, products.price, products.image_url, products.stock
        FROM cart 
        JOIN products ON cart.product_id = products.id 
        WHERE cart.user_id = ?
    ''', (session['user_id'],)).fetchall()
    conn.close()
    
    total = sum(item['price'] * item['quantity'] for item in cart_items)
    cart_count = get_cart_count(session['user_id'])
    
    return render_template('cart.html', cart_items=cart_items, total=total, cart_count=cart_count)

# Sepete ekle
@app.route('/add_to_cart/<int:product_id>')
def add_to_cart(product_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Giriş yapın!'})
    
    conn = get_db_connection()
    
    existing = conn.execute('SELECT * FROM cart WHERE user_id = ? AND product_id = ?', 
                           (session['user_id'], product_id)).fetchone()
    
    if existing:
        conn.execute('UPDATE cart SET quantity = quantity + 1 WHERE id = ?', (existing['id'],))
    else:
        conn.execute('INSERT INTO cart (user_id, product_id) VALUES (?, ?)', 
                    (session['user_id'], product_id))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Ürün sepete eklendi!'})

# Sepetten sil
@app.route('/remove_from_cart/<int:cart_id>')
def remove_from_cart(cart_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    conn.execute('DELETE FROM cart WHERE id = ? AND user_id = ?', (cart_id, session['user_id']))
    conn.commit()
    conn.close()
    
    flash('Ürün sepetten kaldırıldı!', 'success')
    return redirect(url_for('cart'))

# Sipariş oluştur
@app.route('/create_order', methods=['POST'])
def create_order():
    if 'user_id' not in session:
        flash('Sipariş oluşturmak için giriş yapın!', 'error')
        return redirect(url_for('login'))
    
    name = request.form['name']
    email = request.form['email']
    phone = request.form['phone']
    address = request.form['address']
    
    conn = get_db_connection()
    
    # Sepet ürünlerini al
    cart_items = conn.execute('''
        SELECT cart.*, products.name, products.price, products.image_url, products.stock
        FROM cart 
        JOIN products ON cart.product_id = products.id 
        WHERE cart.user_id = ?
    ''', (session['user_id'],)).fetchall()
    
    if not cart_items:
        flash('Sepetiniz boş!', 'error')
        return redirect(url_for('cart'))
    
    # Toplam tutarı hesapla
    total_amount = sum(item['price'] * item['quantity'] for item in cart_items)
    
    # Sipariş oluştur
    cursor = conn.execute('''
        INSERT INTO orders (user_id, total_amount, customer_name, customer_email, customer_phone, customer_address, status)
        VALUES (?, ?, ?, ?, ?, ?, 'pending')
    ''', (session['user_id'], total_amount, name, email, phone, address))
    
    order_id = cursor.lastrowid
    
    # Sipariş ürünlerini ekle (RESİM BİLGİSİ DE EKLENDİ)
    for item in cart_items:
        conn.execute('''
            INSERT INTO order_items (order_id, product_id, product_name, product_image, quantity, price)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (order_id, item['product_id'], item['name'], item['image_url'], item['quantity'], item['price']))
        
        # Stok güncelle
        conn.execute('UPDATE products SET stock = stock - ? WHERE id = ?', 
                    (item['quantity'], item['product_id']))
    
    # Sepeti temizle
    conn.execute('DELETE FROM cart WHERE user_id = ?', (session['user_id'],))
    
    conn.commit()
    conn.close()
    
    flash('Siparişiniz başarıyla oluşturuldu!', 'success')
    return redirect(url_for('index'))

# ADMIN PANELİ - GELİŞMİŞ
@app.route('/admin')
def admin():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Admin erişimi için giriş yapın!', 'error')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    
    # İstatistikler
    stats = conn.execute('''
        SELECT 
            COUNT(*) as total_orders,
            COALESCE(SUM(total_amount), 0) as total_revenue,
            COUNT(DISTINCT user_id) as total_customers,
            COUNT(*) as total_products,
            SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_orders,
            SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending_orders
        FROM orders
    ''').fetchone()
    
    # Son siparişler (MÜŞTERİ BİLGİLERİYLE)
    orders = conn.execute('''
        SELECT o.*, u.email as user_email 
        FROM orders o 
        JOIN users u ON o.user_id = u.id 
        ORDER BY o.created_at DESC 
        LIMIT 10
    ''').fetchall()
    
    # Sipariş ürünleri
    order_items = {}
    for order in orders:
        items = conn.execute('SELECT * FROM order_items WHERE order_id = ?', (order['id'],)).fetchall()
        order_items[order['id']] = items
    
    # Ürünler
    products = conn.execute('''
        SELECT p.*, c.name as category_name 
        FROM products p 
        JOIN categories c ON p.category_id = c.id 
        ORDER BY p.id DESC 
        LIMIT 10
    ''').fetchall()
    
    # Kategoriler
    categories = conn.execute('SELECT * FROM categories').fetchall()
    
    conn.close()
    
    return render_template('admin.html', 
                         stats=stats,
                         orders=orders,
                         order_items=order_items,
                         products=products,
                         categories=categories)

# Admin - Sipariş durumu güncelle
@app.route('/admin/update_order_status', methods=['POST'])
def admin_update_order_status():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Yetkisiz erişim!', 'error')
        return redirect(url_for('admin'))
    
    order_id = request.form['order_id']
    status = request.form['status']
    
    conn = get_db_connection()
    conn.execute('UPDATE orders SET status = ? WHERE id = ?', (status, order_id))
    conn.commit()
    conn.close()
    
    flash('Sipariş durumu güncellendi!', 'success')
    return redirect(url_for('admin'))

# Admin - Ürün ekle
@app.route('/admin/add_product', methods=['POST'])
def admin_add_product():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Yetkisiz erişim!', 'error')
        return redirect(url_for('admin'))
    
    try:
        name = request.form['name']
        description = request.form['description']
        price = float(request.form['price'])
        category_id = int(request.form['category_id'])
        stock = int(request.form['stock'])
        
        # Resim yükleme
        image_url = None
        if 'image' in request.files:
            file = request.files['image']
            image_url = save_image(file)
        
        # Eğer resim yüklenmediyse, varsayılan resim kullan
        if not image_url:
            image_url = '/static/images/default-product.jpg'
        
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO products (name, description, price, category_id, image_url, stock) 
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (name, description, price, category_id, image_url, stock))
        conn.commit()
        conn.close()
        
        flash('Ürün başarıyla eklendi!', 'success')
        return redirect(url_for('admin'))
        
    except Exception as e:
        flash(f'Ürün eklenirken hata: {str(e)}', 'error')
        return redirect(url_for('admin'))

# Admin - Ürün sil
@app.route('/admin/delete_product/<int:product_id>')
def admin_delete_product(product_id):
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Yetkisiz erişim!', 'error')
        return redirect(url_for('admin'))
    
    conn = get_db_connection()
    conn.execute('DELETE FROM products WHERE id = ?', (product_id,))
    conn.commit()
    conn.close()
    
    flash('Ürün başarıyla silindi!', 'success')
    return redirect(url_for('admin'))

# Admin - Kategori ekle
@app.route('/admin/add_category', methods=['POST'])
def admin_add_category():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Yetkisiz erişim!', 'error')
        return redirect(url_for('admin'))
    
    name = request.form['name']
    description = request.form['description']
    
    conn = get_db_connection()
    conn.execute('INSERT INTO categories (name, description) VALUES (?, ?)', (name, description))
    conn.commit()
    conn.close()
    
    flash('Kategori başarıyla eklendi!', 'success')
    return redirect(url_for('admin'))

# Admin - Kategori sil
@app.route('/admin/delete_category/<int:category_id>')
def admin_delete_category(category_id):
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Yetkisiz erişim!', 'error')
        return redirect(url_for('admin'))
    
    conn = get_db_connection()
    
    # Kategoriye ait ürün var mı kontrol et
    products_count = conn.execute('SELECT COUNT(*) as count FROM products WHERE category_id = ?', (category_id,)).fetchone()['count']
    
    if products_count > 0:
        flash('Bu kategoriye ait ürünler var! Önce ürünleri silin.', 'error')
        conn.close()
        return redirect(url_for('admin'))
    
    conn.execute('DELETE FROM categories WHERE id = ?', (category_id,))
    conn.commit()
    conn.close()
    
    flash('Kategori başarıyla silindi!', 'success')
    return redirect(url_for('admin'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)