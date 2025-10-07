import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import List, Dict
from models import Product, Order, OrderStatus, InventoryTransaction, TransactionType
from datetime import datetime, timedelta

def format_currency(amount: float) -> str:
    """Format amount as currency"""
    return f"${amount:.2f}"

def format_datetime(dt: datetime) -> str:
    """Format datetime for display"""
    return dt.strftime("%Y-%m-%d %H:%M")

def create_products_dataframe(products: List[Product]) -> pd.DataFrame:
    """Create DataFrame from products list"""
    data = []
    for product in products:
        data.append({
            'ID': product.id,
            'Name': product.name,
            'Price': format_currency(product.price),
            'Stock': product.stock_quantity,
            'Reserved': product.reserved_quantity,
            'Available': product.available_quantity,
            'Low Stock': '⚠️' if product.is_low_stock else '✅',
            'Threshold': product.low_stock_threshold
        })
    return pd.DataFrame(data)

def create_orders_dataframe(orders: List[Order]) -> pd.DataFrame:
    """Create DataFrame from orders list"""
    data = []
    for order in orders:
        data.append({
            'Order ID': order.id,
            'Customer ID': order.customer_id,
            'Status': order.status.value.title(),
            'Total': format_currency(order.total_amount),
            'Items': len(order.items),
            'Created': format_datetime(order.created_at),
            'Updated': format_datetime(order.updated_at)
        })
    return pd.DataFrame(data)

def create_transactions_dataframe(transactions: List[InventoryTransaction]) -> pd.DataFrame:
    """Create DataFrame from inventory transactions"""
    data = []
    for transaction in transactions:
        data.append({
            'ID': transaction.id,
            'Product ID': transaction.product_id,
            'Type': transaction.transaction_type.value.title(),
            'Quantity': transaction.quantity,
            'Order ID': transaction.order_id or 'N/A',
            'Notes': transaction.notes or 'N/A',
            'Timestamp': format_datetime(transaction.timestamp)
        })
    return pd.DataFrame(data)

def show_inventory_overview_chart(products: List[Product]):
    """Display inventory overview chart"""
    if not products:
        st.info("No products available")
        return
    
    # Prepare data
    names = [p.name for p in products]
    stock = [p.stock_quantity for p in products]
    reserved = [p.reserved_quantity for p in products]
    available = [p.available_quantity for p in products]
    
    # Create stacked bar chart
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='Available',
        x=names,
        y=available,
        marker_color='green'
    ))
    
    fig.add_trace(go.Bar(
        name='Reserved',
        x=names,
        y=reserved,
        marker_color='orange'
    ))
    
    fig.update_layout(
        title='Inventory Overview',
        xaxis_title='Products',
        yaxis_title='Quantity',
        barmode='stack',
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)

def show_order_status_chart(orders: List[Order]):
    """Display order status distribution chart"""
    if not orders:
        st.info("No orders available")
        return
    
    # Count orders by status
    status_counts = {}
    for order in orders:
        status = order.status.value.title()
        status_counts[status] = status_counts.get(status, 0) + 1
    
    # Create pie chart
    fig = px.pie(
        values=list(status_counts.values()),
        names=list(status_counts.keys()),
        title='Order Status Distribution'
    )
    
    st.plotly_chart(fig, use_container_width=True)

def show_sales_overview(orders: List[Order]):
    """Display sales overview metrics"""
    if not orders:
        st.info("No orders available")
        return
    
    # Calculate metrics
    total_orders = len(orders)
    paid_orders = [o for o in orders if o.status in [OrderStatus.PAID, OrderStatus.DELIVERED]]
    total_revenue = sum(o.total_amount for o in paid_orders)
    pending_orders = [o for o in orders if o.status == OrderStatus.PLACED]
    pending_value = sum(o.total_amount for o in pending_orders)
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Orders", total_orders)
    
    with col2:
        st.metric("Paid Orders", len(paid_orders))
    
    with col3:
        st.metric("Total Revenue", format_currency(total_revenue))
    
    with col4:
        st.metric("Pending Value", format_currency(pending_value))

def show_low_stock_alerts(products: List[Product]):
    """Display low stock alerts"""
    low_stock_products = [p for p in products if p.is_low_stock]
    
    if low_stock_products:
        st.warning(f"⚠️ {len(low_stock_products)} products have low stock!")
        
        for product in low_stock_products:
            with st.expander(f"{product.name} - Only {product.stock_quantity} left"):
                st.write(f"**Current Stock:** {product.stock_quantity}")
                st.write(f"**Reserved:** {product.reserved_quantity}")
                st.write(f"**Available:** {product.available_quantity}")
                st.write(f"**Threshold:** {product.low_stock_threshold}")
    else:
        st.success("✅ All products are well stocked!")

def calculate_order_metrics(orders: List[Order]) -> Dict:
    """Calculate various order metrics"""
    now = datetime.now()
    today = now.date()
    week_ago = now - timedelta(days=7)
    
    # Filter orders by timeframe
    today_orders = [o for o in orders if o.created_at.date() == today]
    week_orders = [o for o in orders if o.created_at >= week_ago]
    
    # Calculate metrics
    metrics = {
        'total_orders': len(orders),
        'today_orders': len(today_orders),
        'week_orders': len(week_orders),
        'placed_orders': len([o for o in orders if o.status == OrderStatus.PLACED]),
        'paid_orders': len([o for o in orders if o.status == OrderStatus.PAID]),
        'delivered_orders': len([o for o in orders if o.status == OrderStatus.DELIVERED]),
        'cancelled_orders': len([o for o in orders if o.status == OrderStatus.CANCELLED]),
        'total_revenue': sum(o.total_amount for o in orders if o.status in [OrderStatus.PAID, OrderStatus.DELIVERED]),
        'pending_revenue': sum(o.total_amount for o in orders if o.status == OrderStatus.PLACED)
    }
    
    return metrics

def show_order_timeline(orders: List[Order]):
    """Display order timeline chart"""
    if not orders:
        st.info("No orders available")
        return
    
    # Prepare data for timeline
    df_data = []
    for order in orders:
        df_data.append({
            'Date': order.created_at.date(),
            'Orders': 1,
            'Revenue': order.total_amount if order.status in [OrderStatus.PAID, OrderStatus.DELIVERED] else 0
        })
    
    if not df_data:
        return
    
    df = pd.DataFrame(df_data)
    df_grouped = df.groupby('Date').agg({
        'Orders': 'sum',
        'Revenue': 'sum'
    }).reset_index()
    
    # Create timeline chart
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df_grouped['Date'],
        y=df_grouped['Orders'],
        mode='lines+markers',
        name='Orders',
        yaxis='y'
    ))
    
    fig.add_trace(go.Scatter(
        x=df_grouped['Date'],
        y=df_grouped['Revenue'],
        mode='lines+markers',
        name='Revenue ($)',
        yaxis='y2'
    ))
    
    fig.update_layout(
        title='Orders and Revenue Timeline',
        xaxis_title='Date',
        yaxis=dict(title='Number of Orders', side='left'),
        yaxis2=dict(title='Revenue ($)', side='right', overlaying='y'),
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)
