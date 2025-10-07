import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
from auth import initialize_auth, is_authenticated, show_login_form, show_user_info, get_current_user, has_role, require_auth, require_role
from models import UserRole, OrderStatus, TransactionType, OrderItem
from database import db
from utils import (
    format_currency, create_products_dataframe, create_orders_dataframe, 
    create_transactions_dataframe, show_inventory_overview_chart, show_order_status_chart,
    show_sales_overview, show_low_stock_alerts, calculate_order_metrics, show_order_timeline
)

# Page configuration
st.set_page_config(
    page_title="OmniTrack - Order & Inventory Management",
    page_icon="🏪",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    """Main application function"""
    initialize_auth()
    
    if not is_authenticated():
        show_login_form()
    else:
        show_authenticated_app()

def show_authenticated_app():
    """Show the main application for authenticated users"""
    show_user_info()
    
    user = get_current_user()
    
    if not user:
        st.error("User session not found. Please log in again.")
        return
    
    # Navigation based on user role
    if user.role == UserRole.ADMIN:
        show_admin_interface()
    elif user.role == UserRole.STAFF:
        show_staff_interface()
    elif user.role == UserRole.CUSTOMER:
        show_customer_interface()

def show_admin_interface():
    """Admin interface with full system access"""
    st.title("🔧 Admin Dashboard")
    
    # Sidebar navigation
    with st.sidebar:
        st.header("Admin Menu")
        page = st.selectbox(
            "Select Page",
            ["Dashboard", "Products", "Orders", "Inventory", "Analytics", "Users"]
        )
    
    if page == "Dashboard":
        show_admin_dashboard()
    elif page == "Products":
        show_product_management()
    elif page == "Orders":
        show_order_management()
    elif page == "Inventory":
        show_inventory_management()
    elif page == "Analytics":
        show_analytics_dashboard()
    elif page == "Users":
        show_user_management()

def show_admin_dashboard():
    """Admin dashboard overview"""
    st.header("System Overview")
    
    # Get data
    products = db.get_all_products()
    orders = db.get_all_orders()
    transactions = db.get_all_transactions()
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Products", len(products))
    
    with col2:
        st.metric("Total Orders", len(orders))
    
    with col3:
        low_stock_count = len(db.get_low_stock_products())
        st.metric("Low Stock Items", low_stock_count, delta=f"-{low_stock_count}" if low_stock_count > 0 else None)
    
    with col4:
        pending_orders = len([o for o in orders if o.status == OrderStatus.PLACED])
        st.metric("Pending Orders", pending_orders)
    
    # Charts and alerts
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Inventory Overview")
        show_inventory_overview_chart(products[:10])  # Show top 10 products
    
    with col2:
        st.subheader("Order Status")
        show_order_status_chart(orders)
    
    # Low stock alerts
    st.subheader("Stock Alerts")
    show_low_stock_alerts(products)
    
    # Recent orders
    st.subheader("Recent Orders")
    recent_orders = sorted(orders, key=lambda x: x.created_at, reverse=True)[:5]
    if recent_orders:
        df = create_orders_dataframe(recent_orders)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No orders available")

def show_product_management():
    """Product management interface"""
    st.header("Product Management")
    
    # Add new product
    with st.expander("Add New Product"):
        with st.form("add_product_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                name = st.text_input("Product Name")
                price = st.number_input("Price ($)", min_value=0.01, format="%.2f")
                stock = st.number_input("Initial Stock", min_value=0, value=0)
            
            with col2:
                description = st.text_area("Description")
                threshold = st.number_input("Low Stock Threshold", min_value=1, value=10)
            
            if st.form_submit_button("Add Product"):
                if name and price > 0:
                    product = db.create_product(name, description, price, stock, threshold)
                    st.success(f"Product '{product.name}' added successfully!")
                    st.rerun()
                else:
                    st.error("Please fill in all required fields")
    
    # Products list
    st.subheader("Current Products")
    products = db.get_all_products()
    
    if products:
        # Search and filter
        col1, col2 = st.columns([3, 1])
        with col1:
            search_term = st.text_input("Search products...")
        with col2:
            show_low_stock_only = st.checkbox("Low stock only")
        
        # Filter products
        filtered_products = products
        if search_term:
            filtered_products = [p for p in filtered_products if search_term.lower() in p.name.lower()]
        if show_low_stock_only:
            filtered_products = [p for p in filtered_products if p.is_low_stock]
        
        # Display products
        df = create_products_dataframe(filtered_products)
        st.dataframe(df, use_container_width=True)
        
        # Product actions
        st.subheader("Product Actions")
        selected_product_id = st.selectbox(
            "Select Product",
            options=[p.id for p in filtered_products],
            format_func=lambda x: next(p.name for p in filtered_products if p.id == x)
        )
        
        if selected_product_id:
            product = db.get_product_by_id(selected_product_id)
            if not product:
                st.error("Product not found")
                return
                
            col1, col2, col3 = st.columns(3)
            
            with col1:
                with st.form("restock_form"):
                    restock_qty = st.number_input("Restock Quantity", min_value=1, value=10)
                    if st.form_submit_button("Restock"):
                        current_user = get_current_user()
                        user_id = current_user.id if current_user else None
                        if db.restock_product(selected_product_id, restock_qty, user_id):
                            st.success(f"Added {restock_qty} units to stock")
                            st.rerun()
            
            with col2:
                with st.form("edit_price_form"):
                    new_price = st.number_input("New Price ($)", min_value=0.01, value=product.price, format="%.2f")
                    if st.form_submit_button("Update Price"):
                        if db.update_product(selected_product_id, price=new_price):
                            st.success("Price updated successfully")
                            st.rerun()
            
            with col3:
                with st.form("edit_threshold_form"):
                    new_threshold = st.number_input("Low Stock Threshold", min_value=1, value=product.low_stock_threshold)
                    if st.form_submit_button("Update Threshold"):
                        if db.update_product(selected_product_id, low_stock_threshold=new_threshold):
                            st.success("Threshold updated successfully")
                            st.rerun()
    else:
        st.info("No products available")

def show_order_management():
    """Order management interface"""
    st.header("Order Management")
    
    orders = db.get_all_orders()
    
    if orders:
        # Filter orders
        col1, col2 = st.columns([2, 1])
        with col1:
            status_filter = st.selectbox(
                "Filter by Status",
                options=["All"] + [status.value.title() for status in OrderStatus],
                index=0
            )
        with col2:
            sort_by = st.selectbox("Sort by", ["Newest", "Oldest", "Amount High", "Amount Low"])
        
        # Apply filters
        filtered_orders = orders
        if status_filter != "All":
            status_enum = OrderStatus(status_filter.lower())
            filtered_orders = [o for o in filtered_orders if o.status == status_enum]
        
        # Apply sorting
        if sort_by == "Newest":
            filtered_orders = sorted(filtered_orders, key=lambda x: x.created_at, reverse=True)
        elif sort_by == "Oldest":
            filtered_orders = sorted(filtered_orders, key=lambda x: x.created_at)
        elif sort_by == "Amount High":
            filtered_orders = sorted(filtered_orders, key=lambda x: x.total_amount, reverse=True)
        elif sort_by == "Amount Low":
            filtered_orders = sorted(filtered_orders, key=lambda x: x.total_amount)
        
        # Display orders
        df = create_orders_dataframe(filtered_orders)
        st.dataframe(df, use_container_width=True)
        
        # Order details and actions
        if filtered_orders:
            st.subheader("Order Actions")
            selected_order_id = st.selectbox(
                "Select Order",
                options=[o.id for o in filtered_orders],
                format_func=lambda x: f"Order #{x} - {format_currency(next(o.total_amount for o in filtered_orders if o.id == x))}"
            )
            
            if selected_order_id:
                order = db.get_order_by_id(selected_order_id)
                if not order:
                    st.error("Order not found")
                    return
                
                # Order details
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.write(f"**Order ID:** {order.id}")
                    st.write(f"**Customer ID:** {order.customer_id}")
                    st.write(f"**Status:** {order.status.value.title()}")
                    st.write(f"**Total:** {format_currency(order.total_amount)}")
                    st.write(f"**Created:** {order.created_at}")
                    
                    st.write("**Items:**")
                    for item in order.items:
                        product = db.get_product_by_id(item.product_id)
                        if product:
                            st.write(f"- {product.name}: {item.quantity} × {format_currency(item.unit_price)} = {format_currency(item.total_price)}")
                
                with col2:
                    if order.status == OrderStatus.PLACED:
                        if st.button("Mark as Paid", use_container_width=True):
                            current_user = get_current_user()
                            user_id = current_user.id if current_user else None
                            if db.update_order_status(selected_order_id, OrderStatus.PAID, user_id):
                                st.success("Order marked as paid")
                                st.rerun()
                    
                    if order.status == OrderStatus.PAID:
                        if st.button("Mark as Delivered", use_container_width=True):
                            current_user = get_current_user()
                            user_id = current_user.id if current_user else None
                            if db.update_order_status(selected_order_id, OrderStatus.DELIVERED, user_id):
                                st.success("Order marked as delivered")
                                st.rerun()
                    
                    if order.status in [OrderStatus.PLACED, OrderStatus.PAID]:
                        if st.button("Cancel Order", use_container_width=True):
                            current_user = get_current_user()
                            user_id = current_user.id if current_user else None
                            if db.update_order_status(selected_order_id, OrderStatus.CANCELLED, user_id):
                                st.success("Order cancelled")
                                st.rerun()
    else:
        st.info("No orders available")

def show_inventory_management():
    """Inventory management interface"""
    st.header("Inventory Management")
    
    # Inventory transactions
    st.subheader("Recent Transactions")
    transactions = db.get_all_transactions()
    
    if transactions:
        # Filter transactions
        col1, col2 = st.columns(2)
        with col1:
            transaction_type = st.selectbox(
                "Filter by Type",
                options=["All"] + [t.value.title() for t in TransactionType]
            )
        with col2:
            products_list = db.get_all_products()
            product_filter = st.selectbox(
                "Filter by Product",
                options=[0] + [p.id for p in products_list],
                format_func=lambda x: "All Products" if x == 0 else (db.get_product_by_id(x).name if db.get_product_by_id(x) else "Unknown")
            )
        
        # Apply filters
        filtered_transactions = transactions
        if transaction_type != "All":
            type_enum = TransactionType(transaction_type.lower())
            filtered_transactions = [t for t in filtered_transactions if t.transaction_type == type_enum]
        if product_filter != 0:
            filtered_transactions = [t for t in filtered_transactions if t.product_id == product_filter]
        
        # Sort by timestamp (newest first)
        filtered_transactions = sorted(filtered_transactions, key=lambda x: x.timestamp, reverse=True)
        
        # Display transactions (limit to last 50)
        df = create_transactions_dataframe(filtered_transactions[:50])
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No inventory transactions available")
    
    # Stock overview
    st.subheader("Stock Overview")
    products = db.get_all_products()
    show_inventory_overview_chart(products)
    
    # Low stock alerts
    st.subheader("Stock Alerts")
    show_low_stock_alerts(products)

def show_analytics_dashboard():
    """Analytics dashboard"""
    st.header("Analytics Dashboard")
    
    orders = db.get_all_orders()
    products = db.get_all_products()
    
    # Sales overview
    st.subheader("Sales Overview")
    show_sales_overview(orders)
    
    # Order timeline
    st.subheader("Order Timeline")
    show_order_timeline(orders)
    
    # Order status distribution
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Order Status Distribution")
        show_order_status_chart(orders)
    
    with col2:
        st.subheader("Top Products by Revenue")
        if orders:
            # Calculate revenue by product
            product_revenue = {}
            for order in orders:
                if order.status in [OrderStatus.PAID, OrderStatus.DELIVERED]:
                    for item in order.items:
                        product_revenue[item.product_id] = product_revenue.get(item.product_id, 0) + item.total_price
            
            if product_revenue:
                # Sort by revenue
                top_products = sorted(product_revenue.items(), key=lambda x: x[1], reverse=True)[:5]
                
                revenue_data = []
                for product_id, revenue in top_products:
                    product = db.get_product_by_id(product_id)
                    if product:
                        revenue_data.append({'Product': product.name, 'Revenue': revenue})
                
                if revenue_data:
                    st.bar_chart(data=revenue_data, x='Product', y='Revenue')
            else:
                st.info("No revenue data available")
        else:
            st.info("No orders available")

def show_user_management():
    """User management interface"""
    st.header("User Management")
    
    # Create new user
    with st.expander("Create New User"):
        with st.form("create_user_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
            
            with col2:
                email = st.text_input("Email")
                role = st.selectbox("Role", options=[role.value for role in UserRole])
            
            if st.form_submit_button("Create User"):
                if username and password:
                    existing_user = db.get_user_by_username(username)
                    if existing_user:
                        st.error("Username already exists")
                    else:
                        role_enum = UserRole(role)
                        user = db.create_user(username, password, role_enum, email)
                        st.success(f"User '{user.username}' created successfully!")
                        st.rerun()
                else:
                    st.error("Please fill in username and password")
    
    # Current users
    st.subheader("Current Users")
    users = list(st.session_state.users.values())
    
    if users:
        user_data = []
        for user in users:
            user_data.append({
                'ID': user.id,
                'Username': user.username,
                'Role': user.role.value.title(),
                'Email': user.email,
                'Created': user.created_at.strftime("%Y-%m-%d")
            })
        
        import pandas as pd
        df = pd.DataFrame(user_data)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No users available")

def show_staff_interface():
    """Staff interface for order processing"""
    st.title("👥 Staff Dashboard")
    
    with st.sidebar:
        st.header("Staff Menu")
        page = st.selectbox("Select Page", ["Dashboard", "Orders", "Products"])
    
    if page == "Dashboard":
        show_staff_dashboard()
    elif page == "Orders":
        show_staff_orders()
    elif page == "Products":
        show_staff_products()

def show_staff_dashboard():
    """Staff dashboard overview"""
    st.header("Staff Overview")
    
    orders = db.get_all_orders()
    products = db.get_all_products()
    
    # Key metrics for staff
    col1, col2, col3 = st.columns(3)
    
    with col1:
        pending_orders = len([o for o in orders if o.status == OrderStatus.PLACED])
        st.metric("Pending Orders", pending_orders)
    
    with col2:
        paid_orders = len([o for o in orders if o.status == OrderStatus.PAID])
        st.metric("Ready to Ship", paid_orders)
    
    with col3:
        low_stock_count = len(db.get_low_stock_products())
        st.metric("Low Stock Items", low_stock_count)
    
    # Recent orders requiring attention
    st.subheader("Orders Requiring Attention")
    pending_orders = [o for o in orders if o.status in [OrderStatus.PLACED, OrderStatus.PAID]]
    pending_orders = sorted(pending_orders, key=lambda x: x.created_at)
    
    if pending_orders:
        df = create_orders_dataframe(pending_orders)
        st.dataframe(df, use_container_width=True)
    else:
        st.success("No pending orders!")
    
    # Low stock alerts
    st.subheader("Stock Alerts")
    show_low_stock_alerts(products)

def show_staff_orders():
    """Staff order management"""
    st.header("Order Processing")
    
    orders = db.get_all_orders()
    
    # Filter orders that need staff attention
    actionable_orders = [o for o in orders if o.status in [OrderStatus.PLACED, OrderStatus.PAID]]
    
    if actionable_orders:
        for order in sorted(actionable_orders, key=lambda x: x.created_at):
            with st.expander(f"Order #{order.id} - {order.status.value.title()} - {format_currency(order.total_amount)}"):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.write(f"**Customer ID:** {order.customer_id}")
                    st.write(f"**Created:** {order.created_at}")
                    st.write(f"**Items:**")
                    
                    for item in order.items:
                        product = db.get_product_by_id(item.product_id)
                        if product:
                            st.write(f"- {product.name}: {item.quantity} × {format_currency(item.unit_price)}")
                
                with col2:
                    if order.status == OrderStatus.PLACED:
                        if st.button(f"Process Payment #{order.id}", use_container_width=True):
                            current_user = get_current_user()
                            user_id = current_user.id if current_user else None
                            if db.update_order_status(order.id, OrderStatus.PAID, user_id):
                                st.success("Payment processed!")
                                st.rerun()
                    
                    elif order.status == OrderStatus.PAID:
                        if st.button(f"Mark Delivered #{order.id}", use_container_width=True):
                            current_user = get_current_user()
                            user_id = current_user.id if current_user else None
                            if db.update_order_status(order.id, OrderStatus.DELIVERED, user_id):
                                st.success("Order marked as delivered!")
                                st.rerun()
    else:
        st.success("No orders requiring attention!")
    
    # Show all orders for reference
    st.subheader("All Orders")
    if orders:
        df = create_orders_dataframe(orders)
        st.dataframe(df, use_container_width=True)

def show_staff_products():
    """Staff product view"""
    st.header("Product Information")
    
    products = db.get_all_products()
    
    if products:
        # Search functionality
        search_term = st.text_input("Search products...")
        
        # Filter products
        filtered_products = products
        if search_term:
            filtered_products = [p for p in filtered_products if search_term.lower() in p.name.lower()]
        
        # Display products
        df = create_products_dataframe(filtered_products)
        st.dataframe(df, use_container_width=True)
        
        # Inventory overview
        st.subheader("Inventory Overview")
        show_inventory_overview_chart(filtered_products[:10])
    else:
        st.info("No products available")

def show_customer_interface():
    """Customer interface for shopping"""
    st.title("🛒 Customer Portal")
    
    with st.sidebar:
        st.header("Customer Menu")
        page = st.selectbox("Select Page", ["Shop", "My Orders", "Cart"])
    
    if page == "Shop":
        show_customer_shop()
    elif page == "My Orders":
        show_customer_orders()
    elif page == "Cart":
        show_customer_cart()

def show_customer_shop():
    """Customer shopping interface"""
    st.header("Product Catalog")
    
    # Initialize cart in session state
    if 'cart' not in st.session_state:
        st.session_state.cart = {}
    
    products = db.get_all_products()
    available_products = [p for p in products if p.available_quantity > 0]
    
    if available_products:
        # Search and filter
        col1, col2 = st.columns([3, 1])
        with col1:
            search_term = st.text_input("Search products...")
        with col2:
            sort_by = st.selectbox("Sort by", ["Name", "Price Low", "Price High"])
        
        # Filter products
        filtered_products = available_products
        if search_term:
            filtered_products = [p for p in filtered_products if search_term.lower() in p.name.lower()]
        
        # Sort products
        if sort_by == "Name":
            filtered_products = sorted(filtered_products, key=lambda x: x.name)
        elif sort_by == "Price Low":
            filtered_products = sorted(filtered_products, key=lambda x: x.price)
        elif sort_by == "Price High":
            filtered_products = sorted(filtered_products, key=lambda x: x.price, reverse=True)
        
        # Display products in grid
        cols = st.columns(3)
        for idx, product in enumerate(filtered_products):
            with cols[idx % 3]:
                st.subheader(product.name)
                st.write(f"**Price:** {format_currency(product.price)}")
                st.write(f"**Available:** {product.available_quantity}")
                st.write(f"**Description:** {product.description}")
                
                # Add to cart
                quantity = st.number_input(
                    f"Quantity for {product.name}",
                    min_value=0,
                    max_value=product.available_quantity,
                    value=0,
                    key=f"qty_{product.id}"
                )
                
                if st.button(f"Add to Cart", key=f"add_{product.id}"):
                    if quantity > 0:
                        if product.id in st.session_state.cart:
                            st.session_state.cart[product.id] += quantity
                        else:
                            st.session_state.cart[product.id] = quantity
                        st.success(f"Added {quantity} {product.name}(s) to cart!")
                        st.rerun()
                
                st.divider()
    else:
        st.info("No products available for purchase")
    
    # Show cart summary
    if st.session_state.cart:
        st.sidebar.subheader("Cart Summary")
        total_items = sum(st.session_state.cart.values())
        st.sidebar.write(f"**Total Items:** {total_items}")
        
        total_amount = 0
        for product_id, quantity in st.session_state.cart.items():
            product = db.get_product_by_id(product_id)
            if product:
                item_total = product.price * quantity
                total_amount += item_total
                st.sidebar.write(f"{product.name}: {quantity} × {format_currency(product.price)} = {format_currency(item_total)}")
        
        st.sidebar.write(f"**Total:** {format_currency(total_amount)}")
        
        if st.sidebar.button("Proceed to Checkout"):
            st.session_state.checkout_mode = True
            st.rerun()

def show_customer_cart():
    """Customer cart and checkout"""
    st.header("Shopping Cart")
    
    # Initialize cart if not exists
    if 'cart' not in st.session_state:
        st.session_state.cart = {}
    
    if st.session_state.cart:
        # Display cart items
        st.subheader("Cart Items")
        
        total_amount = 0
        cart_items = []
        
        for product_id, quantity in st.session_state.cart.items():
            product = db.get_product_by_id(product_id)
            if product and product.available_quantity >= quantity:
                item_total = product.price * quantity
                total_amount += item_total
                cart_items.append({
                    'Product': product.name,
                    'Price': format_currency(product.price),
                    'Quantity': quantity,
                    'Total': format_currency(item_total)
                })
            else:
                st.error(f"Product {product.name if product else 'Unknown'} is no longer available in requested quantity")
        
        if cart_items:
            import pandas as pd
            df = pd.DataFrame(cart_items)
            st.dataframe(df, use_container_width=True)
            
            st.write(f"**Grand Total: {format_currency(total_amount)}**")
            
            # Checkout actions
            col1, col2, col3 = st.columns([1, 1, 1])
            
            with col1:
                if st.button("Clear Cart", use_container_width=True):
                    st.session_state.cart = {}
                    st.rerun()
            
            with col2:
                if st.button("Update Cart", use_container_width=True):
                    st.info("Use the shop page to modify quantities")
            
            with col3:
                if st.button("Place Order", use_container_width=True):
                    # Create order
                    order_items = []
                    for product_id, quantity in st.session_state.cart.items():
                        product = db.get_product_by_id(product_id)
                        if product:
                            order_items.append(OrderItem(product_id, quantity, product.price))
                    
                    current_user = get_current_user()
                    user_id = current_user.id if current_user else 0
                    order = db.create_order(user_id, order_items)
                    if order:
                        st.success(f"Order #{order.id} placed successfully!")
                        st.session_state.cart = {}
                        st.rerun()
                    else:
                        st.error("Failed to place order. Some items may be out of stock.")
    else:
        st.info("Your cart is empty. Visit the shop to add items!")

def show_customer_orders():
    """Customer order history"""
    st.header("My Orders")
    
    current_user = get_current_user()
    user_id = current_user.id if current_user else 0
    customer_orders = db.get_orders_by_customer(user_id)
    
    if customer_orders:
        # Sort orders by creation date (newest first)
        customer_orders = sorted(customer_orders, key=lambda x: x.created_at, reverse=True)
        
        for order in customer_orders:
            status_color = {
                OrderStatus.PLACED: "🟡",
                OrderStatus.PAID: "🔵", 
                OrderStatus.DELIVERED: "🟢",
                OrderStatus.CANCELLED: "🔴"
            }.get(order.status, "⚪")
            
            with st.expander(f"{status_color} Order #{order.id} - {order.status.value.title()} - {format_currency(order.total_amount)}"):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.write(f"**Order Date:** {order.created_at.strftime('%Y-%m-%d %H:%M')}")
                    st.write(f"**Status:** {order.status.value.title()}")
                    st.write(f"**Total Amount:** {format_currency(order.total_amount)}")
                    
                    if order.paid_at:
                        st.write(f"**Paid Date:** {order.paid_at.strftime('%Y-%m-%d %H:%M')}")
                    if order.delivered_at:
                        st.write(f"**Delivered Date:** {order.delivered_at.strftime('%Y-%m-%d %H:%M')}")
                    
                    st.write("**Items:**")
                    for item in order.items:
                        product = db.get_product_by_id(item.product_id)
                        if product:
                            st.write(f"- {product.name}: {item.quantity} × {format_currency(item.unit_price)} = {format_currency(item.total_price)}")
                
                with col2:
                    if order.status == OrderStatus.PLACED:
                        st.info("⏳ Waiting for payment processing")
                    elif order.status == OrderStatus.PAID:
                        st.info("📦 Being prepared for delivery")
                    elif order.status == OrderStatus.DELIVERED:
                        st.success("✅ Order completed")
                    elif order.status == OrderStatus.CANCELLED:
                        st.error("❌ Order cancelled")
    else:
        st.info("You haven't placed any orders yet. Visit the shop to start shopping!")

if __name__ == "__main__":
    main()
