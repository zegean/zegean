from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'emin123_ticaret_sitesi'
app.config['DATABASE'] = 'eticaret.db'

def get_db_connection():
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    
    # Tabloları oluştur
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            is_admin BOOLEAN DEFAULT FALSE
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            category_id INTEGER,
            image_url TEXT,
            stock INTEGER DEFAULT 0,
            FOREIGN KEY (category_id) REFERENCES categories (id)
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS cart (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            product_id INTEGER,
            quantity INTEGER DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (product_id) REFERENCES products (id)
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            total_amount REAL,
            status TEXT DEFAULT 'pending',
            customer_name TEXT,
            customer_address TEXT,
            customer_phone TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            product_id INTEGER,
            product_name TEXT,
            quantity INTEGER,
            price REAL,
            FOREIGN KEY (order_id) REFERENCES orders (id),
            FOREIGN KEY (product_id) REFERENCES products (id)
        )
    ''')
    
    # Admin kullanıcısı
    admin_user = conn.execute('SELECT * FROM users WHERE email = ?', ('emin123@gmail.com',)).fetchone()
    if not admin_user:
        admin_password = generate_password_hash('11223344')
        conn.execute('INSERT INTO users (email, password, is_admin) VALUES (?, ?, ?)',
                    ('emin123@gmail.com', admin_password, True))
        print("Admin kullanıcısı eklendi!")
    
    # Kategoriler
    categories_count = conn.execute('SELECT COUNT(*) as count FROM categories').fetchone()['count']
    if categories_count == 0:
        categories = [
            ('Zeytinyağı', 'Kaliteli zeytinyağları'),
            ('Zeytin', 'Çeşit çeşit zeytinler'),
            ('Yöresel Lezzetler', 'Yöresel ürünler'),
            ('Kişisel Bakım', 'Doğal bakım ürünleri'),
            ('Sağlık Destek Ürünleri', 'Sağlıklı yaşam ürünleri'),
            ('Bahçe Ürünleri', 'Bahçe ve doğa ürünleri')
        ]
        conn.executemany('INSERT INTO categories (name, description) VALUES (?, ?)', categories)
        print("Kategoriler eklendi!")
    
    # Ürünler
    products_count = conn.execute('SELECT COUNT(*) as count FROM products').fetchone()['count']
    if products_count == 0:
        products = [
            ('Naturel Sızma Zeytinyağı', 'Soğuk sıkım naturel sızma zeytinyağı', 125.90, 1, '/static/images/oil1.jpg', 50),
            ('Erken Hasat Zeytinyağı', 'Erken hasat premium zeytinyağı', 145.50, 1, '/static/images/oil2.jpg', 30),
            ('Organik Yeşil Zeytin', 'Organik yetiştirilmiş yeşil zeytin', 45.50, 2, '/static/images/olive1.jpg', 100),
            ('Siyah Zeytin', 'Doğal siyah zeytin', 35.00, 2, '/static/images/olive2.jpg', 80),
            ('Köy Peyniri', 'Geleneksel köy peyniri', 85.00, 3, '/static/images/cheese1.jpg', 30),
            ('Zeytinyağlı Sabun', 'Doğal zeytinyağlı sabun', 25.00, 4, '/static/images/soap1.jpg', 75),
            ('Zeytin Yaprağı Çayı', 'Doğal zeytin yaprağı çayı', 35.00, 5, '/static/images/tea1.jpg', 60),
            ('Zeytin Fidanı', 'Verimli zeytin fidanı', 55.00, 6, '/static/images/tree1.jpg', 40),
            ('Zeytin Yaprağı Ekstresi', 'Doğal zeytin yaprağı ekstresi', 75.00, 5, '/static/images/extract.jpg', 25),
            ('Zeytin Ağacı', 'Yetişkin zeytin ağacı', 450.00, 6, '/static/images/tree2.jpg', 15)
        ]
        conn.executemany('INSERT INTO products (name, description, price, category_id, image_url, stock) VALUES (?, ?, ?, ?, ?, ?)', products)
        print("Ürünler eklendi!")
    
    conn.commit()
    conn.close()
    print("Veritabanı hazır!")

# Sepet sayısını hesapla
def get_cart_count(user_id):
    try:
        conn = get_db_connection()
        count = conn.execute('SELECT SUM(quantity) as total FROM cart WHERE user_id = ?', (user_id,)).fetchone()['total']
        conn.close()
        return count or 0
    except:
        return 0

# Ana sayfa
@app.route('/')
def index():
    try:
        conn = get_db_connection()
        products = conn.execute('SELECT * FROM products LIMIT 8').fetchall()
        categories = conn.execute('SELECT * FROM categories').fetchall()
        conn.close()
        
        cart_count = 0
        if 'user_id' in session:
            cart_count = get_cart_count(session['user_id'])
        
        return render_template('index.html', products=products, categories=categories, cart_count=cart_count)
    except Exception as e:
        print(f"Hata: {e}")
        return "Veritabanı hatası! Sayfayı yenileyin."

# Arama
@app.route('/search')
def search():
    try:
        query = request.args.get('q', '')
        conn = get_db_connection()
        
        if query:
            products = conn.execute('''
                SELECT * FROM products 
                WHERE name LIKE ? OR description LIKE ?
            ''', (f'%{query}%', f'%{query}%')).fetchall()
        else:
            products = conn.execute('SELECT * FROM products LIMIT 8').fetchall()
        
        categories = conn.execute('SELECT * FROM categories').fetchall()
        conn.close()
        
        cart_count = 0
        if 'user_id' in session:
            cart_count = get_cart_count(session['user_id'])
        
        return render_template('index.html', products=products, categories=categories, search_query=query, cart_count=cart_count)
    except Exception as e:
        print(f"Hata: {e}")
        return "Veritabanı hatası!"

# Giriş sayfası
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        try:
            conn = get_db_connection()
            user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
            conn.close()
            
            if user and check_password_hash(user['password'], password):
                session['user_id'] = user['id']
                session['user_email'] = user['email']
                session['is_admin'] = user['is_admin']
                flash('Başarıyla giriş yapıldı!', 'success')
                return redirect(url_for('index'))
            else:
                flash('E-posta veya şifre hatalı!', 'error')
        except Exception as e:
            flash('Veritabanı hatası!', 'error')
    
    return render_template('login.html')

# Kayıt sayfası
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            flash('Şifreler eşleşmiyor!', 'error')
            return render_template('register.html')
        
        try:
            conn = get_db_connection()
            existing_user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
            
            if existing_user:
                flash('Bu e-posta zaten kullanılıyor!', 'error')
                conn.close()
                return render_template('register.html')
            
            hashed_password = generate_password_hash(password)
            conn.execute('INSERT INTO users (email, password) VALUES (?, ?)', (email, hashed_password))
            conn.commit()
            conn.close()
            
            flash('Kayıt başarılı! Giriş yapabilirsiniz.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash('Veritabanı hatası!', 'error')
    
    return render_template('register.html')

# Çıkış
@app.route('/logout')
def logout():
    session.clear()
    flash('Çıkış yapıldı!', 'info')
    return redirect(url_for('index'))

# Kategori sayfası
@app.route('/category/<int:category_id>')
def category(category_id):
    try:
        conn = get_db_connection()
        category = conn.execute('SELECT * FROM categories WHERE id = ?', (category_id,)).fetchone()
        products = conn.execute('SELECT * FROM products WHERE category_id = ?', (category_id,)).fetchall()
        categories = conn.execute('SELECT * FROM categories').fetchall()
        conn.close()
        
        cart_count = 0
        if 'user_id' in session:
            cart_count = get_cart_count(session['user_id'])
        
        return render_template('category.html', category=category, products=products, categories=categories, cart_count=cart_count)
    except Exception as e:
        flash('Kategori bulunamadı!', 'error')
        return redirect(url_for('index'))

# Sepet
@app.route('/cart')
def cart():
    if 'user_id' not in session:
        flash('Sepeti görüntülemek için giriş yapın!', 'error')
        return redirect(url_for('login'))
    
    try:
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
    except Exception as e:
        flash('Sepet yüklenirken hata!', 'error')
        return redirect(url_for('index'))

# Sepete ekle
@app.route('/add_to_cart/<int:product_id>')
def add_to_cart(product_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Giriş yapın!'})
    
    try:
        conn = get_db_connection()
        
        # Stok kontrolü
        product = conn.execute('SELECT stock FROM products WHERE id = ?', (product_id,)).fetchone()
        if not product or product['stock'] <= 0:
            return jsonify({'success': False, 'message': 'Ürün stokta yok!'})
        
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
    except Exception as e:
        return jsonify({'success': False, 'message': 'Hata oluştu!'})

# Sepetten sil
@app.route('/remove_from_cart/<int:cart_id>')
def remove_from_cart(cart_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Giriş yapın!'})
    
    try:
        conn = get_db_connection()
        conn.execute('DELETE FROM cart WHERE id = ? AND user_id = ?', (cart_id, session['user_id']))
        conn.commit()
        conn.close()
        
        flash('Ürün sepetten kaldırıldı!', 'success')
        return redirect(url_for('cart'))
    except Exception as e:
        flash('Ürün kaldırılırken hata!', 'error')
        return redirect(url_for('cart'))

# Sipariş oluştur
@app.route('/create_order', methods=['POST'])
def create_order():
    if 'user_id' not in session:
        flash('Sipariş oluşturmak için giriş yapın!', 'error')
        return redirect(url_for('login'))
    
    try:
        name = request.form['name']
        address = request.form['address']
        phone = request.form['phone']
        
        conn = get_db_connection()
        
        # Sepet ürünlerini al
        cart_items = conn.execute('''
            SELECT cart.*, products.name, products.price, products.stock
            FROM cart 
            JOIN products ON cart.product_id = products.id 
            WHERE cart.user_id = ?
        ''', (session['user_id'],)).fetchall()
        
        if not cart_items:
            flash('Sepetiniz boş!', 'error')
            return redirect(url_for('cart'))
        
        # Stok kontrolü
        for item in cart_items:
            if item['quantity'] > item['stock']:
                flash(f'{item["name"]} ürününden yeterli stok yok!', 'error')
                return redirect(url_for('cart'))
        
        # Toplam tutarı hesapla
        total_amount = sum(item['price'] * item['quantity'] for item in cart_items)
        
        # Sipariş oluştur
        cursor = conn.execute('''
            INSERT INTO orders (user_id, total_amount, customer_name, customer_address, customer_phone, status)
            VALUES (?, ?, ?, ?, ?, 'pending')
        ''', (session['user_id'], total_amount, name, address, phone))
        
        order_id = cursor.lastrowid
        
        # Sipariş ürünlerini ekle
        for item in cart_items:
            conn.execute('''
                INSERT INTO order_items (order_id, product_id, product_name, quantity, price)
                VALUES (?, ?, ?, ?, ?)
            ''', (order_id, item['product_id'], item['name'], item['quantity'], item['price']))
            
            # Stok güncelle
            conn.execute('UPDATE products SET stock = stock - ? WHERE id = ?', 
                        (item['quantity'], item['product_id']))
        
        # Sepeti temizle
        conn.execute('DELETE FROM cart WHERE user_id = ?', (session['user_id'],))
        
        conn.commit()
        conn.close()
        
        flash('Siparişiniz başarıyla oluşturuldu!', 'success')
        return redirect(url_for('index'))
        
    except Exception as e:
        print(f"Sipariş hatası: {e}")
        flash('Sipariş oluşturulurken hata!', 'error')
        return redirect(url_for('cart'))

# Admin paneli
@app.route('/admin')
def admin():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Admin erişimi için giriş yapın!', 'error')
        return redirect(url_for('login'))
    
    try:
        conn = get_db_connection()
        
        # Siparişler (tüm detaylarıyla)
        orders = conn.execute('''
            SELECT orders.*, users.email, 
                   (SELECT COUNT(*) FROM order_items WHERE order_id = orders.id) as item_count
            FROM orders 
            JOIN users ON orders.user_id = users.id 
            ORDER BY orders.created_at DESC
        ''').fetchall()
        
        # Sipariş detayları
        order_details = {}
        for order in orders:
            items = conn.execute('''
                SELECT * FROM order_items WHERE order_id = ?
            ''', (order['id'],)).fetchall()
            order_details[order['id']] = items
        
        # Ürünler
        products = conn.execute('''
            SELECT products.*, categories.name as category_name 
            FROM products 
            JOIN categories ON products.category_id = categories.id
            ORDER BY products.id DESC
        ''').fetchall()
        
        # Kategoriler
        categories = conn.execute('SELECT * FROM categories ORDER BY name').fetchall()
        
        # Kullanıcılar
        users = conn.execute('SELECT * FROM users ORDER BY id').fetchall()
        
        # İstatistikler
        stats = conn.execute('''
            SELECT 
                COUNT(*) as total_orders,
                COALESCE(SUM(total_amount), 0) as total_revenue,
                COALESCE(AVG(total_amount), 0) as avg_order_value,
                COUNT(DISTINCT user_id) as total_customers,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_orders,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending_orders
            FROM orders
        ''').fetchone()
        
        conn.close()
        
        return render_template('admin.html', 
                             orders=orders, 
                             order_details=order_details,
                             products=products, 
                             categories=categories, 
                             users=users, 
                             stats=stats)
    except Exception as e:
        print(f"Admin paneli hatası: {e}")
        flash('Admin paneli yüklenirken hata!', 'error')
        return redirect(url_for('index'))

# Ürün ekle (Admin)
@app.route('/admin/add_product', methods=['POST'])
def add_product():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Yetkisiz erişim!', 'error')
        return redirect(url_for('admin'))
    
    try:
        name = request.form['name']
        description = request.form['description']
        price = float(request.form['price'])
        category_id = int(request.form['category_id'])
        stock = int(request.form['stock'])
        
        conn = get_db_connection()
        conn.execute('INSERT INTO products (name, description, price, category_id, stock) VALUES (?, ?, ?, ?, ?)',
                    (name, description, price, category_id, stock))
        conn.commit()
        conn.close()
        
        flash('Ürün başarıyla eklendi!', 'success')
        return redirect(url_for('admin'))
    except Exception as e:
        flash('Ürün eklenirken hata!', 'error')
        return redirect(url_for('admin'))

# Sipariş durumu güncelle
@app.route('/admin/update_order_status', methods=['POST'])
def update_order_status():
    if 'user_id' not in session or not session.get('is_admin'):
        return jsonify({'success': False, 'message': 'Yetkisiz erişim!'})
    
    try:
        order_id = request.form['order_id']
        status = request.form['status']
        
        conn = get_db_connection()
        conn.execute('UPDATE orders SET status = ? WHERE id = ?', (status, order_id))
        conn.commit()
        conn.close()
        
        flash('Sipariş durumu güncellendi!', 'success')
        return redirect(url_for('admin'))
    except Exception as e:
        flash('Sipariş güncellenirken hata!', 'error')
        return redirect(url_for('admin'))

# Kategori ekle (Admin)
@app.route('/admin/add_category', methods=['POST'])
def add_category():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Yetkisiz erişim!', 'error')
        return redirect(url_for('admin'))
    
    try:
        name = request.form['name']
        description = request.form['description']
        
        conn = get_db_connection()
        conn.execute('INSERT INTO categories (name, description) VALUES (?, ?)',
                    (name, description))
        conn.commit()
        conn.close()
        
        flash('Kategori başarıyla eklendi!', 'success')
        return redirect(url_for('admin'))
    except Exception as e:
        flash('Kategori eklenirken hata!', 'error')
        return redirect(url_for('admin'))

if __name__ == '__main__':
    # Veritabanını başlat
    init_db()
    app.run(debug=True, port=5000)