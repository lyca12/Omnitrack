import psycopg2
from psycopg2.extras import RealDictCursor
import os
from typing import List, Optional
from models import User, Product, Order, OrderItem, InventoryTransaction, UserRole, OrderStatus, TransactionType
from datetime import datetime

class Database:
    """PostgreSQL database implementation"""
    
    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL')
        self._create_demo_data()
    
    def _get_connection(self):
        """Get a database connection"""
        return psycopg2.connect(self.database_url)
    
    def _create_demo_data(self):
        """Create demo users and products if not already created"""
        if len(self.get_all_users()) == 0:
            demo_users = [
                ("admin", "admin123", "admin", "admin@omnitrack.com"),
                ("staff", "staff123", "staff", "staff@omnitrack.com"),
                ("customer", "customer123", "customer", "customer@example.com")
            ]
            
            for username, password, role, email in demo_users:
                self.create_user(username, password, UserRole(role), email)
        
        if len(self.get_all_products()) == 0:
            demo_products = [
                ("Running Shoes", "High-performance running shoes", 129.99, 25, 5),
                ("Basketball", "Official size basketball", 29.99, 15, 3),
                ("Tennis Racket", "Professional tennis racket", 199.99, 8, 2),
                ("Soccer Ball", "FIFA approved soccer ball", 39.99, 12, 3),
                ("Yoga Mat", "Non-slip yoga mat", 49.99, 20, 5),
                ("Dumbbells Set", "Adjustable dumbbells 5-50 lbs", 299.99, 6, 2),
                ("Sports Water Bottle", "Insulated water bottle", 19.99, 30, 10),
                ("Training T-Shirt", "Moisture-wicking athletic shirt", 24.99, 18, 5)
            ]
            
            for name, description, price, stock, threshold in demo_products:
                self.create_product(name, description, price, stock, threshold)
    
    def create_user(self, username: str, password: str, role: UserRole, email: str = "") -> User:
        """Create a new user"""
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "INSERT INTO users (username, password, role, email) VALUES (%s, %s, %s, %s) RETURNING *",
                    (username, password, role.value, email)
                )
                row = cur.fetchone()
                conn.commit()
                return User(row['id'], row['username'], row['password'], UserRole(row['role']), 
                          row['email'], row['created_at'])
        finally:
            conn.close()
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM users WHERE username = %s", (username,))
                row = cur.fetchone()
                if row:
                    return User(row['id'], row['username'], row['password'], UserRole(row['role']), 
                              row['email'], row['created_at'])
                return None
        finally:
            conn.close()
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
                row = cur.fetchone()
                if row:
                    return User(row['id'], row['username'], row['password'], UserRole(row['role']), 
                              row['email'], row['created_at'])
                return None
        finally:
            conn.close()
    
    def get_all_users(self) -> List[User]:
        """Get all users"""
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM users ORDER BY id")
                rows = cur.fetchall()
                return [User(row['id'], row['username'], row['password'], UserRole(row['role']), 
                           row['email'], row['created_at']) for row in rows]
        finally:
            conn.close()
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate user with username and password"""
        user = self.get_user_by_username(username)
        if user and user.password == password:
            return user
        return None
    
    def create_product(self, name: str, description: str, price: float, stock_quantity: int, low_stock_threshold: int = 10) -> Product:
        """Create a new product"""
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """INSERT INTO products (name, description, price, stock_quantity, reserved_quantity, low_stock_threshold) 
                       VALUES (%s, %s, %s, %s, 0, %s) RETURNING *""",
                    (name, description, price, stock_quantity, low_stock_threshold)
                )
                row = cur.fetchone()
                conn.commit()
                product = Product(row['id'], row['name'], row['description'], float(row['price']), 
                                row['stock_quantity'], row['reserved_quantity'], row['low_stock_threshold'],
                                row['created_at'], row['updated_at'])
                
                self.create_inventory_transaction(product.id, TransactionType.RESTOCK, stock_quantity, notes="Initial stock")
                return product
        finally:
            conn.close()
    
    def get_product_by_id(self, product_id: int) -> Optional[Product]:
        """Get product by ID"""
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM products WHERE id = %s", (product_id,))
                row = cur.fetchone()
                if row:
                    return Product(row['id'], row['name'], row['description'], float(row['price']), 
                                 row['stock_quantity'], row['reserved_quantity'], row['low_stock_threshold'],
                                 row['created_at'], row['updated_at'])
                return None
        finally:
            conn.close()
    
    def get_all_products(self) -> List[Product]:
        """Get all products"""
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM products ORDER BY id")
                rows = cur.fetchall()
                return [Product(row['id'], row['name'], row['description'], float(row['price']), 
                              row['stock_quantity'], row['reserved_quantity'], row['low_stock_threshold'],
                              row['created_at'], row['updated_at']) for row in rows]
        finally:
            conn.close()
    
    def update_product(self, product_id: int, **kwargs) -> bool:
        """Update product fields"""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                set_clauses = []
                values = []
                for key, value in kwargs.items():
                    set_clauses.append(f"{key} = %s")
                    values.append(value)
                
                if set_clauses:
                    set_clauses.append("updated_at = CURRENT_TIMESTAMP")
                    values.append(product_id)
                    query = f"UPDATE products SET {', '.join(set_clauses)} WHERE id = %s"
                    cur.execute(query, values)
                    conn.commit()
                    return cur.rowcount > 0
                return False
        finally:
            conn.close()
    
    def restock_product(self, product_id: int, quantity: int, user_id: Optional[int] = None) -> bool:
        """Add stock to a product"""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE products SET stock_quantity = stock_quantity + %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                    (quantity, product_id)
                )
                conn.commit()
                if cur.rowcount > 0:
                    self.create_inventory_transaction(product_id, TransactionType.RESTOCK, quantity, user_id=user_id)
                    return True
                return False
        finally:
            conn.close()
    
    def reserve_stock(self, product_id: int, quantity: int, order_id: int) -> bool:
        """Reserve stock for an order"""
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT stock_quantity, reserved_quantity FROM products WHERE id = %s", (product_id,))
                row = cur.fetchone()
                if row and (row['stock_quantity'] - row['reserved_quantity']) >= quantity:
                    cur.execute(
                        "UPDATE products SET reserved_quantity = reserved_quantity + %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                        (quantity, product_id)
                    )
                    conn.commit()
                    self.create_inventory_transaction(product_id, TransactionType.RESERVE, quantity, order_id=order_id)
                    return True
                return False
        finally:
            conn.close()
    
    def release_stock(self, product_id: int, quantity: int, order_id: int) -> bool:
        """Release reserved stock"""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE products SET reserved_quantity = reserved_quantity - %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s AND reserved_quantity >= %s",
                    (quantity, product_id, quantity)
                )
                conn.commit()
                if cur.rowcount > 0:
                    self.create_inventory_transaction(product_id, TransactionType.RELEASE, quantity, order_id=order_id)
                    return True
                return False
        finally:
            conn.close()
    
    def sell_product(self, product_id: int, quantity: int, order_id: int) -> bool:
        """Complete sale of product"""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE products SET stock_quantity = stock_quantity - %s, 
                       reserved_quantity = reserved_quantity - %s, updated_at = CURRENT_TIMESTAMP 
                       WHERE id = %s AND reserved_quantity >= %s""",
                    (quantity, quantity, product_id, quantity)
                )
                conn.commit()
                if cur.rowcount > 0:
                    self.create_inventory_transaction(product_id, TransactionType.SALE, quantity, order_id=order_id)
                    return True
                return False
        finally:
            conn.close()
    
    def create_order(self, customer_id: int, items: List[OrderItem]) -> Optional[Order]:
        """Create a new order and reserve stock - all within a single transaction"""
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "INSERT INTO orders (customer_id, status) VALUES (%s, %s) RETURNING *",
                    (customer_id, OrderStatus.PLACED.value)
                )
                order_row = cur.fetchone()
                order_id = order_row['id']
                
                for item in items:
                    cur.execute("SELECT stock_quantity, reserved_quantity FROM products WHERE id = %s FOR UPDATE", (item.product_id,))
                    product_row = cur.fetchone()
                    
                    if not product_row or (product_row['stock_quantity'] - product_row['reserved_quantity']) < item.quantity:
                        conn.rollback()
                        return None
                    
                    cur.execute(
                        "UPDATE products SET reserved_quantity = reserved_quantity + %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                        (item.quantity, item.product_id)
                    )
                    
                    cur.execute(
                        "INSERT INTO inventory_transactions (product_id, transaction_type, quantity, order_id) VALUES (%s, %s, %s, %s)",
                        (item.product_id, TransactionType.RESERVE.value, item.quantity, order_id)
                    )
                    
                    cur.execute(
                        "INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (%s, %s, %s, %s)",
                        (order_id, item.product_id, item.quantity, item.unit_price)
                    )
                
                conn.commit()
                order = Order(order_row['id'], order_row['customer_id'], items, OrderStatus(order_row['status']),
                            order_row['created_at'], order_row['updated_at'], order_row['paid_at'], order_row['delivered_at'])
                return order
        except Exception:
            conn.rollback()
            return None
        finally:
            conn.close()
    
    def get_order_by_id(self, order_id: int) -> Optional[Order]:
        """Get order by ID"""
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM orders WHERE id = %s", (order_id,))
                order_row = cur.fetchone()
                if not order_row:
                    return None
                
                cur.execute("SELECT * FROM order_items WHERE order_id = %s", (order_id,))
                item_rows = cur.fetchall()
                items = [OrderItem(row['product_id'], row['quantity'], float(row['unit_price'])) for row in item_rows]
                
                return Order(order_row['id'], order_row['customer_id'], items, OrderStatus(order_row['status']),
                           order_row['created_at'], order_row['updated_at'], order_row['paid_at'], order_row['delivered_at'])
        finally:
            conn.close()
    
    def get_orders_by_customer(self, customer_id: int) -> List[Order]:
        """Get all orders for a customer"""
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM orders WHERE customer_id = %s ORDER BY created_at DESC", (customer_id,))
                order_rows = cur.fetchall()
                
                orders = []
                for order_row in order_rows:
                    cur.execute("SELECT * FROM order_items WHERE order_id = %s", (order_row['id'],))
                    item_rows = cur.fetchall()
                    items = [OrderItem(row['product_id'], row['quantity'], float(row['unit_price'])) for row in item_rows]
                    
                    orders.append(Order(order_row['id'], order_row['customer_id'], items, OrderStatus(order_row['status']),
                                      order_row['created_at'], order_row['updated_at'], order_row['paid_at'], order_row['delivered_at']))
                
                return orders
        finally:
            conn.close()
    
    def get_all_orders(self) -> List[Order]:
        """Get all orders"""
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM orders ORDER BY created_at DESC")
                order_rows = cur.fetchall()
                
                orders = []
                for order_row in order_rows:
                    cur.execute("SELECT * FROM order_items WHERE order_id = %s", (order_row['id'],))
                    item_rows = cur.fetchall()
                    items = [OrderItem(row['product_id'], row['quantity'], float(row['unit_price'])) for row in item_rows]
                    
                    orders.append(Order(order_row['id'], order_row['customer_id'], items, OrderStatus(order_row['status']),
                                      order_row['created_at'], order_row['updated_at'], order_row['paid_at'], order_row['delivered_at']))
                
                return orders
        finally:
            conn.close()
    
    def update_order_status(self, order_id: int, status: OrderStatus, user_id: Optional[int] = None) -> bool:
        """Update order status - all inventory operations in single transaction"""
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM orders WHERE id = %s", (order_id,))
                order_row = cur.fetchone()
                if not order_row:
                    return False
                
                update_fields = ["status = %s", "updated_at = CURRENT_TIMESTAMP"]
                params = [status.value]
                
                if status == OrderStatus.PAID:
                    update_fields.append("paid_at = CURRENT_TIMESTAMP")
                    cur.execute("SELECT * FROM order_items WHERE order_id = %s", (order_id,))
                    item_rows = cur.fetchall()
                    for item_row in item_rows:
                        cur.execute(
                            """UPDATE products SET stock_quantity = stock_quantity - %s, 
                               reserved_quantity = reserved_quantity - %s, updated_at = CURRENT_TIMESTAMP 
                               WHERE id = %s AND reserved_quantity >= %s""",
                            (item_row['quantity'], item_row['quantity'], item_row['product_id'], item_row['quantity'])
                        )
                        cur.execute(
                            "INSERT INTO inventory_transactions (product_id, transaction_type, quantity, order_id, user_id) VALUES (%s, %s, %s, %s, %s)",
                            (item_row['product_id'], TransactionType.SALE.value, item_row['quantity'], order_id, user_id)
                        )
                        
                elif status == OrderStatus.DELIVERED:
                    update_fields.append("delivered_at = CURRENT_TIMESTAMP")
                    
                elif status == OrderStatus.CANCELLED:
                    cur.execute("SELECT * FROM order_items WHERE order_id = %s", (order_id,))
                    item_rows = cur.fetchall()
                    for item_row in item_rows:
                        cur.execute(
                            "UPDATE products SET reserved_quantity = reserved_quantity - %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s AND reserved_quantity >= %s",
                            (item_row['quantity'], item_row['product_id'], item_row['quantity'])
                        )
                        cur.execute(
                            "INSERT INTO inventory_transactions (product_id, transaction_type, quantity, order_id, user_id) VALUES (%s, %s, %s, %s, %s)",
                            (item_row['product_id'], TransactionType.RELEASE.value, item_row['quantity'], order_id, user_id)
                        )
                
                params.append(order_id)
                query = f"UPDATE orders SET {', '.join(update_fields)} WHERE id = %s"
                cur.execute(query, params)
                conn.commit()
                return cur.rowcount > 0
        except Exception:
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def create_inventory_transaction(self, product_id: int, transaction_type: TransactionType, quantity: int, 
                                   order_id: Optional[int] = None, user_id: Optional[int] = None, notes: str = "") -> InventoryTransaction:
        """Create a new inventory transaction"""
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """INSERT INTO inventory_transactions (product_id, transaction_type, quantity, order_id, user_id, notes) 
                       VALUES (%s, %s, %s, %s, %s, %s) RETURNING *""",
                    (product_id, transaction_type.value, quantity, order_id, user_id, notes)
                )
                row = cur.fetchone()
                conn.commit()
                return InventoryTransaction(row['id'], row['product_id'], TransactionType(row['transaction_type']),
                                          row['quantity'], row['order_id'], row['user_id'], row['notes'], row['timestamp'])
        finally:
            conn.close()
    
    def get_transactions_by_product(self, product_id: int) -> List[InventoryTransaction]:
        """Get all transactions for a product"""
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM inventory_transactions WHERE product_id = %s ORDER BY timestamp DESC", (product_id,))
                rows = cur.fetchall()
                return [InventoryTransaction(row['id'], row['product_id'], TransactionType(row['transaction_type']),
                                            row['quantity'], row['order_id'], row['user_id'], row['notes'], row['timestamp']) 
                       for row in rows]
        finally:
            conn.close()
    
    def get_all_transactions(self) -> List[InventoryTransaction]:
        """Get all inventory transactions"""
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM inventory_transactions ORDER BY timestamp DESC")
                rows = cur.fetchall()
                return [InventoryTransaction(row['id'], row['product_id'], TransactionType(row['transaction_type']),
                                            row['quantity'], row['order_id'], row['user_id'], row['notes'], row['timestamp']) 
                       for row in rows]
        finally:
            conn.close()
    
    def get_low_stock_products(self) -> List[Product]:
        """Get products with low stock"""
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM products WHERE stock_quantity <= low_stock_threshold ORDER BY stock_quantity")
                rows = cur.fetchall()
                return [Product(row['id'], row['name'], row['description'], float(row['price']), 
                              row['stock_quantity'], row['reserved_quantity'], row['low_stock_threshold'],
                              row['created_at'], row['updated_at']) for row in rows]
        finally:
            conn.close()

db = Database()
