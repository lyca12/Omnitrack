from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum

class UserRole(Enum):
    ADMIN = "admin"
    STAFF = "staff"
    CUSTOMER = "customer"

class OrderStatus(Enum):
    PLACED = "placed"
    PAID = "paid"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

class TransactionType(Enum):
    RESERVE = "reserve"
    SALE = "sale"
    RELEASE = "release"
    RESTOCK = "restock"

@dataclass
class User:
    id: int
    username: str
    password: str
    role: UserRole
    email: str = ""
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class Product:
    id: int
    name: str
    description: str
    price: float
    stock_quantity: int
    reserved_quantity: int = 0
    low_stock_threshold: int = 10
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    @property
    def available_quantity(self) -> int:
        return self.stock_quantity - self.reserved_quantity
    
    @property
    def is_low_stock(self) -> bool:
        return self.stock_quantity <= self.low_stock_threshold

@dataclass
class OrderItem:
    product_id: int
    quantity: int
    unit_price: float
    
    @property
    def total_price(self) -> float:
        return self.quantity * self.unit_price

@dataclass
class Order:
    id: int
    customer_id: int
    items: List[OrderItem]
    status: OrderStatus
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    paid_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    
    @property
    def total_amount(self) -> float:
        return sum(item.total_price for item in self.items)

@dataclass
class InventoryTransaction:
    id: int
    product_id: int
    transaction_type: TransactionType
    quantity: int
    order_id: Optional[int] = None
    user_id: Optional[int] = None
    notes: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

