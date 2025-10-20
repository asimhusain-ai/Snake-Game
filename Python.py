"""
Restaurant Management System
A comprehensive Python application demonstrating:
- Object-Oriented Programming
- Database Integration
- GUI Development
- API Development
- File Handling
- Testing
- Design Patterns
- Advanced Python Features
"""

import json
import csv
import sqlite3
import datetime
import hashlib
import uuid
import logging
import threading
import queue
import time
from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Dict, Optional, Union, Tuple
from dataclasses import dataclass
from contextlib import contextmanager
import random
import re
from decimal import Decimal
import pickle
import asyncio
import aiohttp
from functools import wraps
import inspect

# ==================== CONFIGURATION AND CONSTANTS ====================

class Config:
    """Configuration class for the restaurant system"""
    DATABASE_PATH = "restaurant.db"
    LOG_FILE = "restaurant.log"
    MAX_TABLES = 20
    MAX_ORDER_ITEMS = 50
    TAX_RATE = Decimal('0.08')
    DEFAULT_CURRENCY = "USD"
    
    # Menu categories
    CATEGORIES = ["Appetizers", "Main Course", "Desserts", "Beverages", "Specials"]
    
    # Order statuses
    ORDER_STATUS = ["pending", "confirmed", "preparing", "ready", "served", "paid", "cancelled"]

# ==================== LOGGING SETUP ====================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Config.LOG_FILE),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("RestaurantSystem")

# ==================== DECORATORS ====================

def log_execution_time(func):
    """Decorator to log function execution time"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        execution_time = time.time() - start_time
        logger.info(f"{func.__name__} executed in {execution_time:.4f} seconds")
        return result
    return wrapper

def validate_input(validation_func):
    """Decorator for input validation"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get function signature
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            
            # Validate arguments
            for param_name, param_value in bound_args.arguments.items():
                if not validation_func(param_name, param_value):
                    raise ValueError(f"Invalid input for {param_name}: {param_value}")
            
            return func(*args, **kwargs)
        return wrapper
    return decorator

# ==================== EXCEPTIONS ====================

class RestaurantException(Exception):
    """Base exception for restaurant system"""
    pass

class OrderException(RestaurantException):
    """Order-related exceptions"""
    pass

class PaymentException(RestaurantException):
    """Payment-related exceptions"""
    pass

class InventoryException(RestaurantException):
    """Inventory-related exceptions"""
    pass

# ==================== ENUMS ====================

class OrderStatus(Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PREPARING = "preparing"
    READY = "ready"
    SERVED = "served"
    PAID = "paid"
    CANCELLED = "cancelled"

class PaymentMethod(Enum):
    CASH = "cash"
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    DIGITAL_WALLET = "digital_wallet"

class UserRole(Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    CHEF = "chef"
    WAITER = "waiter"
    CUSTOMER = "customer"

# ==================== BASE CLASSES AND ABSTRACTIONS ====================

class Entity(ABC):
    """Abstract base class for all entities"""
    
    def __init__(self, id: str = None):
        self.id = id or str(uuid.uuid4())
        self.created_at = datetime.datetime.now()
        self.updated_at = datetime.datetime.now()
    
    @abstractmethod
    def to_dict(self) -> Dict:
        """Convert entity to dictionary"""
        pass
    
    @classmethod
    @abstractmethod
    def from_dict(cls, data: Dict):
        """Create entity from dictionary"""
        pass

class Repository(ABC):
    """Abstract base class for repositories"""
    
    @abstractmethod
    def add(self, entity: Entity):
        pass
    
    @abstractmethod
    def get(self, entity_id: str) -> Optional[Entity]:
        pass
    
    @abstractmethod
    def get_all(self) -> List[Entity]:
        pass
    
    @abstractmethod
    def update(self, entity: Entity):
        pass
    
    @abstractmethod
    def delete(self, entity_id: str):
        pass

# ==================== DATABASE MODULE ====================

class DatabaseManager:
    """Manages database connections and operations"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialize()
            return cls._instance
    
    def _initialize(self):
        """Initialize database connection and create tables"""
        self.connection = sqlite3.connect(Config.DATABASE_PATH, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self._create_tables()
    
    def _create_tables(self):
        """Create database tables"""
        tables = [
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                phone TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS menu_items (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                category TEXT NOT NULL,
                price DECIMAL(10,2) NOT NULL,
                cost DECIMAL(10,2) NOT NULL,
                is_available BOOLEAN DEFAULT 1,
                preparation_time INTEGER,
                calories INTEGER,
                image_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS ingredients (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                unit TEXT NOT NULL,
                current_stock DECIMAL(10,3) NOT NULL,
                min_stock DECIMAL(10,3) NOT NULL,
                supplier TEXT,
                unit_cost DECIMAL(10,2) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS menu_ingredients (
                menu_item_id TEXT,
                ingredient_id TEXT,
                quantity DECIMAL(10,3) NOT NULL,
                PRIMARY KEY (menu_item_id, ingredient_id),
                FOREIGN KEY (menu_item_id) REFERENCES menu_items(id),
                FOREIGN KEY (ingredient_id) REFERENCES ingredients(id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS tables (
                id TEXT PRIMARY KEY,
                table_number INTEGER UNIQUE NOT NULL,
                capacity INTEGER NOT NULL,
                location TEXT,
                is_occupied BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS orders (
                id TEXT PRIMARY KEY,
                table_id TEXT,
                customer_id TEXT,
                waiter_id TEXT,
                status TEXT NOT NULL,
                total_amount DECIMAL(10,2) NOT NULL,
                tax_amount DECIMAL(10,2) NOT NULL,
                discount_amount DECIMAL(10,2) DEFAULT 0,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (table_id) REFERENCES tables(id),
                FOREIGN KEY (customer_id) REFERENCES users(id),
                FOREIGN KEY (waiter_id) REFERENCES users(id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS order_items (
                id TEXT PRIMARY KEY,
                order_id TEXT,
                menu_item_id TEXT,
                quantity INTEGER NOT NULL,
                unit_price DECIMAL(10,2) NOT NULL,
                special_instructions TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES orders(id),
                FOREIGN KEY (menu_item_id) REFERENCES menu_items(id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS payments (
                id TEXT PRIMARY KEY,
                order_id TEXT,
                amount DECIMAL(10,2) NOT NULL,
                payment_method TEXT NOT NULL,
                transaction_id TEXT,
                status TEXT NOT NULL,
                tip_amount DECIMAL(10,2) DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES orders(id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS inventory_transactions (
                id TEXT PRIMARY KEY,
                ingredient_id TEXT,
                quantity DECIMAL(10,3) NOT NULL,
                transaction_type TEXT NOT NULL,
                reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (ingredient_id) REFERENCES ingredients(id)
            )
            """
        ]
        
        cursor = self.connection.cursor()
        for table_sql in tables:
            cursor.execute(table_sql)
        self.connection.commit()
    
    @contextmanager
    def get_cursor(self):
        """Context manager for database cursor"""
        cursor = self.connection.cursor()
        try:
            yield cursor
            self.connection.commit()
        except Exception as e:
            self.connection.rollback()
            raise e
        finally:
            cursor.close()
    
    def execute_query(self, query: str, params: Tuple = ()):
        """Execute a query and return results"""
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()
    
    def execute_update(self, query: str, params: Tuple = ()):
        """Execute an update query"""
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            return cursor.rowcount

# ==================== USER MANAGEMENT MODULE ====================

@dataclass
class User(Entity):
    """User entity representing system users"""
    username: str = ""
    email: str = ""
    password_hash: str = ""
    role: UserRole = UserRole.CUSTOMER
    first_name: str = ""
    last_name: str = ""
    phone: str = ""
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'password_hash': self.password_hash,
            'role': self.role.value,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'phone': self.phone,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'User':
        user = cls()
        user.id = data['id']
        user.username = data['username']
        user.email = data['email']
        user.password_hash = data['password_hash']
        user.role = UserRole(data['role'])
        user.first_name = data['first_name']
        user.last_name = data['last_name']
        user.phone = data.get('phone', '')
        user.created_at = datetime.datetime.fromisoformat(data['created_at'])
        user.updated_at = datetime.datetime.fromisoformat(data['updated_at'])
        return user
    
    def set_password(self, password: str):
        """Set password with hashing"""
        self.password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    def verify_password(self, password: str) -> bool:
        """Verify password against hash"""
        return self.password_hash == hashlib.sha256(password.encode()).hexdigest()
    
    def get_full_name(self) -> str:
        """Get user's full name"""
        return f"{self.first_name} {self.last_name}"

class UserRepository(Repository):
    """Repository for user operations"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def add(self, user: User):
        query = """
        INSERT INTO users (id, username, email, password_hash, role, first_name, last_name, phone, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            user.id, user.username, user.email, user.password_hash, 
            user.role.value, user.first_name, user.last_name, user.phone,
            user.created_at, user.updated_at
        )
        self.db_manager.execute_update(query, params)
    
    def get(self, user_id: str) -> Optional[User]:
        query = "SELECT * FROM users WHERE id = ?"
        results = self.db_manager.execute_query(query, (user_id,))
        if results:
            return User.from_dict(dict(results[0]))
        return None
    
    def get_by_username(self, username: str) -> Optional[User]:
        query = "SELECT * FROM users WHERE username = ?"
        results = self.db_manager.execute_query(query, (username,))
        if results:
            return User.from_dict(dict(results[0]))
        return None
    
    def get_by_email(self, email: str) -> Optional[User]:
        query = "SELECT * FROM users WHERE email = ?"
        results = self.db_manager.execute_query(query, (email,))
        if results:
            return User.from_dict(dict(results[0]))
        return None
    
    def get_all(self) -> List[User]:
        query = "SELECT * FROM users ORDER BY created_at DESC"
        results = self.db_manager.execute_query(query)
        return [User.from_dict(dict(row)) for row in results]
    
    def update(self, user: User):
        user.updated_at = datetime.datetime.now()
        query = """
        UPDATE users SET username=?, email=?, password_hash=?, role=?, first_name=?, last_name=?, phone=?, updated_at=?
        WHERE id=?
        """
        params = (
            user.username, user.email, user.password_hash, user.role.value,
            user.first_name, user.last_name, user.phone, user.updated_at, user.id
        )
        self.db_manager.execute_update(query, params)
    
    def delete(self, user_id: str):
        query = "DELETE FROM users WHERE id = ?"
        self.db_manager.execute_update(query, (user_id,))
    
    def get_by_role(self, role: UserRole) -> List[User]:
        query = "SELECT * FROM users WHERE role = ? ORDER BY first_name, last_name"
        results = self.db_manager.execute_query(query, (role.value,))
        return [User.from_dict(dict(row)) for row in results]

class AuthenticationService:
    """Handles user authentication and authorization"""
    
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository
        self._current_user = None
    
    def login(self, username: str, password: str) -> bool:
        """Authenticate user"""
        user = self.user_repository.get_by_username(username)
        if user and user.verify_password(password):
            self._current_user = user
            logger.info(f"User {username} logged in successfully")
            return True
        logger.warning(f"Failed login attempt for username: {username}")
        return False
    
    def logout(self):
        """Logout current user"""
        if self._current_user:
            logger.info(f"User {self._current_user.username} logged out")
        self._current_user = None
    
    def get_current_user(self) -> Optional[User]:
        """Get currently authenticated user"""
        return self._current_user
    
    def has_permission(self, required_role: UserRole) -> bool:
        """Check if current user has required role"""
        if not self._current_user:
            return False
        role_hierarchy = {
            UserRole.ADMIN: [UserRole.ADMIN, UserRole.MANAGER, UserRole.CHEF, UserRole.WAITER, UserRole.CUSTOMER],
            UserRole.MANAGER: [UserRole.MANAGER, UserRole.CHEF, UserRole.WAITER, UserRole.CUSTOMER],
            UserRole.CHEF: [UserRole.CHEF, UserRole.CUSTOMER],
            UserRole.WAITER: [UserRole.WAITER, UserRole.CUSTOMER],
            UserRole.CUSTOMER: [UserRole.CUSTOMER]
        }
        return self._current_user.role in role_hierarchy.get(required_role, [])

# ==================== MENU MANAGEMENT MODULE ====================

@dataclass
class Ingredient(Entity):
    """Ingredient entity for inventory management"""
    name: str = ""
    unit: str = ""
    current_stock: Decimal = Decimal('0')
    min_stock: Decimal = Decimal('0')
    supplier: str = ""
    unit_cost: Decimal = Decimal('0')
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'name': self.name,
            'unit': self.unit,
            'current_stock': float(self.current_stock),
            'min_stock': float(self.min_stock),
            'supplier': self.supplier,
            'unit_cost': float(self.unit_cost),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Ingredient':
        ingredient = cls()
        ingredient.id = data['id']
        ingredient.name = data['name']
        ingredient.unit = data['unit']
        ingredient.current_stock = Decimal(str(data['current_stock']))
        ingredient.min_stock = Decimal(str(data['min_stock']))
        ingredient.supplier = data.get('supplier', '')
        ingredient.unit_cost = Decimal(str(data['unit_cost']))
        ingredient.created_at = datetime.datetime.fromisoformat(data['created_at'])
        ingredient.updated_at = datetime.datetime.fromisoformat(data['updated_at'])
        return ingredient
    
    def is_low_stock(self) -> bool:
        """Check if ingredient is below minimum stock level"""
        return self.current_stock < self.min_stock

@dataclass
class MenuItem(Entity):
    """Menu item entity"""
    name: str = ""
    description: str = ""
    category: str = ""
    price: Decimal = Decimal('0')
    cost: Decimal = Decimal('0')
    is_available: bool = True
    preparation_time: int = 0
    calories: int = 0
    image_url: str = ""
    ingredients: Dict[str, Decimal] = None  # ingredient_id -> quantity
    
    def __post_init__(self):
        if self.ingredients is None:
            self.ingredients = {}
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'price': float(self.price),
            'cost': float(self.cost),
            'is_available': self.is_available,
            'preparation_time': self.preparation_time,
            'calories': self.calories,
            'image_url': self.image_url,
            'ingredients': {k: float(v) for k, v in self.ingredients.items()},
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'MenuItem':
        item = cls()
        item.id = data['id']
        item.name = data['name']
        item.description = data['description']
        item.category = data['category']
        item.price = Decimal(str(data['price']))
        item.cost = Decimal(str(data['cost']))
        item.is_available = data['is_available']
        item.preparation_time = data.get('preparation_time', 0)
        item.calories = data.get('calories', 0)
        item.image_url = data.get('image_url', '')
        item.ingredients = {k: Decimal(str(v)) for k, v in data.get('ingredients', {}).items()}
        item.created_at = datetime.datetime.fromisoformat(data['created_at'])
        item.updated_at = datetime.datetime.fromisoformat(data['updated_at'])
        return item
    
    def calculate_cost(self, ingredient_prices: Dict[str, Decimal]) -> Decimal:
        """Calculate cost based on ingredient prices"""
        total_cost = Decimal('0')
        for ingredient_id, quantity in self.ingredients.items():
            if ingredient_id in ingredient_prices:
                total_cost += ingredient_prices[ingredient_id] * quantity
        return total_cost
    
    def get_profit_margin(self) -> Decimal:
        """Calculate profit margin percentage"""
        if self.cost == 0:
            return Decimal('0')
        return ((self.price - self.cost) / self.cost) * 100

class MenuRepository(Repository):
    """Repository for menu operations"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def add(self, menu_item: MenuItem):
        # Insert menu item
        query = """
        INSERT INTO menu_items (id, name, description, category, price, cost, is_available, preparation_time, calories, image_url, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            menu_item.id, menu_item.name, menu_item.description, menu_item.category,
            float(menu_item.price), float(menu_item.cost), menu_item.is_available,
            menu_item.preparation_time, menu_item.calories, menu_item.image_url,
            menu_item.created_at, menu_item.updated_at
        )
        self.db_manager.execute_update(query, params)
        
        # Insert ingredients
        self._update_menu_ingredients(menu_item)
    
    def get(self, menu_item_id: str) -> Optional[MenuItem]:
        query = "SELECT * FROM menu_items WHERE id = ?"
        results = self.db_manager.execute_query(query, (menu_item_id,))
        if not results:
            return None
        
        menu_item = MenuItem.from_dict(dict(results[0]))
        menu_item.ingredients = self._get_menu_ingredients(menu_item_id)
        return menu_item
    
    def get_all(self) -> List[MenuItem]:
        query = "SELECT * FROM menu_items ORDER BY category, name"
        results = self.db_manager.execute_query(query)
        menu_items = []
        for row in results:
            menu_item = MenuItem.from_dict(dict(row))
            menu_item.ingredients = self._get_menu_ingredients(menu_item.id)
            menu_items.append(menu_item)
        return menu_items
    
    def update(self, menu_item: MenuItem):
        menu_item.updated_at = datetime.datetime.now()
        query = """
        UPDATE menu_items SET name=?, description=?, category=?, price=?, cost=?, is_available=?, 
        preparation_time=?, calories=?, image_url=?, updated_at=? WHERE id=?
        """
        params = (
            menu_item.name, menu_item.description, menu_item.category,
            float(menu_item.price), float(menu_item.cost), menu_item.is_available,
            menu_item.preparation_time, menu_item.calories, menu_item.image_url,
            menu_item.updated_at, menu_item.id
        )
        self.db_manager.execute_update(query, params)
        
        # Update ingredients
        self._update_menu_ingredients(menu_item)
    
    def delete(self, menu_item_id: str):
        # Delete ingredients first
        delete_ingredients_query = "DELETE FROM menu_ingredients WHERE menu_item_id = ?"
        self.db_manager.execute_update(delete_ingredients_query, (menu_item_id,))
        
        # Delete menu item
        delete_query = "DELETE FROM menu_items WHERE id = ?"
        self.db_manager.execute_update(delete_query, (menu_item_id,))
    
    def get_by_category(self, category: str) -> List[MenuItem]:
        query = "SELECT * FROM menu_items WHERE category = ? AND is_available = 1 ORDER BY name"
        results = self.db_manager.execute_query(query, (category,))
        menu_items = []
        for row in results:
            menu_item = MenuItem.from_dict(dict(row))
            menu_item.ingredients = self._get_menu_ingredients(menu_item.id)
            menu_items.append(menu_item)
        return menu_items
    
    def _get_menu_ingredients(self, menu_item_id: str) -> Dict[str, Decimal]:
        query = """
        SELECT i.id, i.name, mi.quantity 
        FROM menu_ingredients mi 
        JOIN ingredients i ON mi.ingredient_id = i.id 
        WHERE mi.menu_item_id = ?
        """
        results = self.db_manager.execute_query(query, (menu_item_id,))
        return {row['id']: Decimal(str(row['quantity'])) for row in results}
    
    def _update_menu_ingredients(self, menu_item: MenuItem):
        # Delete existing ingredients
        delete_query = "DELETE FROM menu_ingredients WHERE menu_item_id = ?"
        self.db_manager.execute_update(delete_query, (menu_item.id,))
        
        # Insert new ingredients
        for ingredient_id, quantity in menu_item.ingredients.items():
            insert_query = """
            INSERT INTO menu_ingredients (menu_item_id, ingredient_id, quantity)
            VALUES (?, ?, ?)
            """
            self.db_manager.execute_update(insert_query, (menu_item.id, ingredient_id, float(quantity)))

class IngredientRepository(Repository):
    """Repository for ingredient operations"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def add(self, ingredient: Ingredient):
        query = """
        INSERT INTO ingredients (id, name, unit, current_stock, min_stock, supplier, unit_cost, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            ingredient.id, ingredient.name, ingredient.unit, 
            float(ingredient.current_stock), float(ingredient.min_stock),
            ingredient.supplier, float(ingredient.unit_cost),
            ingredient.created_at, ingredient.updated_at
        )
        self.db_manager.execute_update(query, params)
    
    def get(self, ingredient_id: str) -> Optional[Ingredient]:
        query = "SELECT * FROM ingredients WHERE id = ?"
        results = self.db_manager.execute_query(query, (ingredient_id,))
        if results:
            return Ingredient.from_dict(dict(results[0]))
        return None
    
    def get_all(self) -> List[Ingredient]:
        query = "SELECT * FROM ingredients ORDER BY name"
        results = self.db_manager.execute_query(query)
        return [Ingredient.from_dict(dict(row)) for row in results]
    
    def update(self, ingredient: Ingredient):
        ingredient.updated_at = datetime.datetime.now()
        query = """
        UPDATE ingredients SET name=?, unit=?, current_stock=?, min_stock=?, supplier=?, unit_cost=?, updated_at=?
        WHERE id=?
        """
        params = (
            ingredient.name, ingredient.unit, float(ingredient.current_stock),
            float(ingredient.min_stock), ingredient.supplier, float(ingredient.unit_cost),
            ingredient.updated_at, ingredient.id
        )
        self.db_manager.execute_update(query, params)
    
    def delete(self, ingredient_id: str):
        query = "DELETE FROM ingredients WHERE id = ?"
        self.db_manager.execute_update(query, (ingredient_id,))
    
    def get_low_stock(self) -> List[Ingredient]:
        query = "SELECT * FROM ingredients WHERE current_stock < min_stock ORDER BY current_stock ASC"
        results = self.db_manager.execute_query(query)
        return [Ingredient.from_dict(dict(row)) for row in results]
    
    def update_stock(self, ingredient_id: str, quantity: Decimal):
        """Update ingredient stock level"""
        query = "UPDATE ingredients SET current_stock = current_stock + ?, updated_at = ? WHERE id = ?"
        params = (float(quantity), datetime.datetime.now(), ingredient_id)
        self.db_manager.execute_update(query, params)

# ==================== ORDER MANAGEMENT MODULE ====================

@dataclass
class OrderItem(Entity):
    """Order item entity"""
    menu_item_id: str = ""
    quantity: int = 0
    unit_price: Decimal = Decimal('0')
    special_instructions: str = ""
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'menu_item_id': self.menu_item_id,
            'quantity': self.quantity,
            'unit_price': float(self.unit_price),
            'special_instructions': self.special_instructions,
            'created_at': self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'OrderItem':
        item = cls()
        item.id = data['id']
        item.menu_item_id = data['menu_item_id']
        item.quantity = data['quantity']
        item.unit_price = Decimal(str(data['unit_price']))
        item.special_instructions = data.get('special_instructions', '')
        item.created_at = datetime.datetime.fromisoformat(data['created_at'])
        return item
    
    def get_total_price(self) -> Decimal:
        """Calculate total price for this order item"""
        return self.unit_price * self.quantity

@dataclass
class Order(Entity):
    """Order entity"""
    table_id: str = ""
    customer_id: str = ""
    waiter_id: str = ""
    status: OrderStatus = OrderStatus.PENDING
    total_amount: Decimal = Decimal('0')
    tax_amount: Decimal = Decimal('0')
    discount_amount: Decimal = Decimal('0')
    notes: str = ""
    items: List[OrderItem] = None
    
    def __post_init__(self):
        if self.items is None:
            self.items = []
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'table_id': self.table_id,
            'customer_id': self.customer_id,
            'waiter_id': self.waiter_id,
            'status': self.status.value,
            'total_amount': float(self.total_amount),
            'tax_amount': float(self.tax_amount),
            'discount_amount': float(self.discount_amount),
            'notes': self.notes,
            'items': [item.to_dict() for item in self.items],
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Order':
        order = cls()
        order.id = data['id']
        order.table_id = data['table_id']
        order.customer_id = data.get('customer_id')
        order.waiter_id = data.get('waiter_id')
        order.status = OrderStatus(data['status'])
        order.total_amount = Decimal(str(data['total_amount']))
        order.tax_amount = Decimal(str(data['tax_amount']))
        order.discount_amount = Decimal(str(data.get('discount_amount', 0)))
        order.notes = data.get('notes', '')
        order.items = [OrderItem.from_dict(item_data) for item_data in data.get('items', [])]
        order.created_at = datetime.datetime.fromisoformat(data['created_at'])
        order.updated_at = datetime.datetime.fromisoformat(data['updated_at'])
        return order
    
    def calculate_totals(self):
        """Calculate order totals"""
        subtotal = sum(item.get_total_price() for item in self.items)
        self.tax_amount = subtotal * Config.TAX_RATE
        self.total_amount = subtotal + self.tax_amount - self.discount_amount
    
    def add_item(self, menu_item: MenuItem, quantity: int = 1, special_instructions: str = ""):
        """Add item to order"""
        if len(self.items) >= Config.MAX_ORDER_ITEMS:
            raise OrderException("Maximum order items reached")
        
        order_item = OrderItem()
        order_item.menu_item_id = menu_item.id
        order_item.quantity = quantity
        order_item.unit_price = menu_item.price
        order_item.special_instructions = special_instructions
        
        self.items.append(order_item)
        self.calculate_totals()
    
    def remove_item(self, order_item_id: str):
        """Remove item from order"""
        self.items = [item for item in self.items if item.id != order_item_id]
        self.calculate_totals()
    
    def update_status(self, new_status: OrderStatus):
        """Update order status"""
        valid_transitions = {
            OrderStatus.PENDING: [OrderStatus.CONFIRMED, OrderStatus.CANCELLED],
            OrderStatus.CONFIRMED: [OrderStatus.PREPARING, OrderStatus.CANCELLED],
            OrderStatus.PREPARING: [OrderStatus.READY, OrderStatus.CANCELLED],
            OrderStatus.READY: [OrderStatus.SERVED],
            OrderStatus.SERVED: [OrderStatus.PAID],
            OrderStatus.PAID: [],
            OrderStatus.CANCELLED: []
        }
        
        if new_status not in valid_transitions.get(self.status, []):
            raise OrderException(f"Invalid status transition from {self.status.value} to {new_status.value}")
        
        self.status = new_status
        self.updated_at = datetime.datetime.now()

class OrderRepository(Repository):
    """Repository for order operations"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def add(self, order: Order):
        # Insert order
        query = """
        INSERT INTO orders (id, table_id, customer_id, waiter_id, status, total_amount, tax_amount, discount_amount, notes, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            order.id, order.table_id, order.customer_id, order.waiter_id,
            order.status.value, float(order.total_amount), float(order.tax_amount),
            float(order.discount_amount), order.notes, order.created_at, order.updated_at
        )
        self.db_manager.execute_update(query, params)
        
        # Insert order items
        for item in order.items:
            self._add_order_item(item, order.id)
    
    def get(self, order_id: str) -> Optional[Order]:
        query = "SELECT * FROM orders WHERE id = ?"
        results = self.db_manager.execute_query(query, (order_id,))
        if not results:
            return None
        
        order = Order.from_dict(dict(results[0]))
        order.items = self._get_order_items(order_id)
        return order
    
    def get_all(self) -> List[Order]:
        query = "SELECT * FROM orders ORDER BY created_at DESC"
        results = self.db_manager.execute_query(query)
        orders = []
        for row in results:
            order = Order.from_dict(dict(row))
            order.items = self._get_order_items(order.id)
            orders.append(order)
        return orders
    
    def update(self, order: Order):
        order.updated_at = datetime.datetime.now()
        query = """
        UPDATE orders SET table_id=?, customer_id=?, waiter_id=?, status=?, total_amount=?, 
        tax_amount=?, discount_amount=?, notes=?, updated_at=? WHERE id=?
        """
        params = (
            order.table_id, order.customer_id, order.waiter_id, order.status.value,
            float(order.total_amount), float(order.tax_amount), float(order.discount_amount),
            order.notes, order.updated_at, order.id
        )
        self.db_manager.execute_update(query, params)
        
        # Update order items (delete and reinsert for simplicity)
        self._delete_order_items(order.id)
        for item in order.items:
            self._add_order_item(item, order.id)
    
    def delete(self, order_id: str):
        # Delete order items first
        self._delete_order_items(order_id)
        
        # Delete order
        query = "DELETE FROM orders WHERE id = ?"
        self.db_manager.execute_update(query, (order_id,))
    
    def get_by_status(self, status: OrderStatus) -> List[Order]:
        query = "SELECT * FROM orders WHERE status = ? ORDER BY created_at ASC"
        results = self.db_manager.execute_query(query, (status.value,))
        orders = []
        for row in results:
            order = Order.from_dict(dict(row))
            order.items = self._get_order_items(order.id)
            orders.append(order)
        return orders
    
    def get_by_table(self, table_id: str) -> List[Order]:
        query = "SELECT * FROM orders WHERE table_id = ? ORDER BY created_at DESC"
        results = self.db_manager.execute_query(query, (table_id,))
        orders = []
        for row in results:
            order = Order.from_dict(dict(row))
            order.items = self._get_order_items(order.id)
            orders.append(order)
        return orders
    
    def _get_order_items(self, order_id: str) -> List[OrderItem]:
        query = "SELECT * FROM order_items WHERE order_id = ?"
        results = self.db_manager.execute_query(query, (order_id,))
        return [OrderItem.from_dict(dict(row)) for row in results]
    
    def _add_order_item(self, order_item: OrderItem, order_id: str):
        query = """
        INSERT INTO order_items (id, order_id, menu_item_id, quantity, unit_price, special_instructions, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            order_item.id, order_id, order_item.menu_item_id, order_item.quantity,
            float(order_item.unit_price), order_item.special_instructions, order_item.created_at
        )
        self.db_manager.execute_update(query, params)
    
    def _delete_order_items(self, order_id: str):
        query = "DELETE FROM order_items WHERE order_id = ?"
        self.db_manager.execute_update(query, (order_id,))

# ==================== PAYMENT MODULE ====================

@dataclass
class Payment(Entity):
    """Payment entity"""
    order_id: str = ""
    amount: Decimal = Decimal('0')
    payment_method: PaymentMethod = PaymentMethod.CASH
    transaction_id: str = ""
    status: str = "pending"
    tip_amount: Decimal = Decimal('0')
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'order_id': self.order_id,
            'amount': float(self.amount),
            'payment_method': self.payment_method.value,
            'transaction_id': self.transaction_id,
            'status': self.status,
            'tip_amount': float(self.tip_amount),
            'created_at': self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Payment':
        payment = cls()
        payment.id = data['id']
        payment.order_id = data['order_id']
        payment.amount = Decimal(str(data['amount']))
        payment.payment_method = PaymentMethod(data['payment_method'])
        payment.transaction_id = data.get('transaction_id', '')
        payment.status = data['status']
        payment.tip_amount = Decimal(str(data.get('tip_amount', 0)))
        payment.created_at = datetime.datetime.fromisoformat(data['created_at'])
        return payment
    
    def process_payment(self) -> bool:
        """Process payment (simulated)"""
        try:
            # Simulate payment processing
            if self.payment_method == PaymentMethod.CASH:
                self.status = "completed"
            else:
                # Simulate card/wallet processing
                if random.random() < 0.95:  # 95% success rate
                    self.status = "completed"
                    self.transaction_id = f"TXN{random.randint(100000, 999999)}"
                else:
                    self.status = "failed"
                    raise PaymentException("Payment processing failed")
            
            logger.info(f"Payment {self.id} processed with status: {self.status}")
            return self.status == "completed"
        except Exception as e:
            logger.error(f"Payment processing error: {e}")
            self.status = "failed"
            return False

class PaymentRepository(Repository):
    """Repository for payment operations"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def add(self, payment: Payment):
        query = """
        INSERT INTO payments (id, order_id, amount, payment_method, transaction_id, status, tip_amount, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            payment.id, payment.order_id, float(payment.amount), payment.payment_method.value,
            payment.transaction_id, payment.status, float(payment.tip_amount), payment.created_at
        )
        self.db_manager.execute_update(query, params)
    
    def get(self, payment_id: str) -> Optional[Payment]:
        query = "SELECT * FROM payments WHERE id = ?"
        results = self.db_manager.execute_query(query, (payment_id,))
        if results:
            return Payment.from_dict(dict(results[0]))
        return None
    
    def get_all(self) -> List[Payment]:
        query = "SELECT * FROM payments ORDER BY created_at DESC"
        results = self.db_manager.execute_query(query)
        return [Payment.from_dict(dict(row)) for row in results]
    
    def update(self, payment: Payment):
        query = """
        UPDATE payments SET order_id=?, amount=?, payment_method=?, transaction_id=?, status=?, tip_amount=?
        WHERE id=?
        """
        params = (
            payment.order_id, float(payment.amount), payment.payment_method.value,
            payment.transaction_id, payment.status, float(payment.tip_amount), payment.id
        )
        self.db_manager.execute_update(query, params)
    
    def delete(self, payment_id: str):
        query = "DELETE FROM payments WHERE id = ?"
        self.db_manager.execute_update(query, (payment_id,))
    
    def get_by_order(self, order_id: str) -> List[Payment]:
        query = "SELECT * FROM payments WHERE order_id = ? ORDER BY created_at DESC"
        results = self.db_manager.execute_query(query, (order_id,))
        return [Payment.from_dict(dict(row)) for row in results]

# ==================== TABLE MANAGEMENT MODULE ====================

@dataclass
class Table(Entity):
    """Table entity"""
    table_number: int = 0
    capacity: int = 0
    location: str = ""
    is_occupied: bool = False
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'table_number': self.table_number,
            'capacity': self.capacity,
            'location': self.location,
            'is_occupied': self.is_occupied,
            'created_at': self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Table':
        table = cls()
        table.id = data['id']
        table.table_number = data['table_number']
        table.capacity = data['capacity']
        table.location = data.get('location', '')
        table.is_occupied = data['is_occupied']
        table.created_at = datetime.datetime.fromisoformat(data['created_at'])
        return table
    
    def occupy(self):
        """Mark table as occupied"""
        if self.is_occupied:
            raise RestaurantException(f"Table {self.table_number} is already occupied")
        self.is_occupied = True
    
    def vacate(self):
        """Mark table as vacant"""
        if not self.is_occupied:
            raise RestaurantException(f"Table {self.table_number} is already vacant")
        self.is_occupied = False

class TableRepository(Repository):
    """Repository for table operations"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def add(self, table: Table):
        query = """
        INSERT INTO tables (id, table_number, capacity, location, is_occupied, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """
        params = (
            table.id, table.table_number, table.capacity, table.location,
            table.is_occupied, table.created_at
        )
        self.db_manager.execute_update(query, params)
    
    def get(self, table_id: str) -> Optional[Table]:
        query = "SELECT * FROM tables WHERE id = ?"
        results = self.db_manager.execute_query(query, (table_id,))
        if results:
            return Table.from_dict(dict(results[0]))
        return None
    
    def get_by_number(self, table_number: int) -> Optional[Table]:
        query = "SELECT * FROM tables WHERE table_number = ?"
        results = self.db_manager.execute_query(query, (table_number,))
        if results:
            return Table.from_dict(dict(results[0]))
        return None
    
    def get_all(self) -> List[Table]:
        query = "SELECT * FROM tables ORDER BY table_number"
        results = self.db_manager.execute_query(query)
        return [Table.from_dict(dict(row)) for row in results]
    
    def update(self, table: Table):
        query = """
        UPDATE tables SET table_number=?, capacity=?, location=?, is_occupied=?
        WHERE id=?
        """
        params = (
            table.table_number, table.capacity, table.location, table.is_occupied, table.id
        )
        self.db_manager.execute_update(query, params)
    
    def delete(self, table_id: str):
        query = "DELETE FROM tables WHERE id = ?"
        self.db_manager.execute_update(query, (table_id,))
    
    def get_available_tables(self) -> List[Table]:
        query = "SELECT * FROM tables WHERE is_occupied = 0 ORDER BY table_number"
        results = self.db_manager.execute_query(query)
        return [Table.from_dict(dict(row)) for row in results]
    
    def get_occupied_tables(self) -> List[Table]:
        query = "SELECT * FROM tables WHERE is_occupied = 1 ORDER BY table_number"
        results = self.db_manager.execute_query(query)
        return [Table.from_dict(dict(row)) for row in results]

# ==================== INVENTORY MANAGEMENT MODULE ====================

class InventoryService:
    """Service for inventory management"""
    
    def __init__(self, ingredient_repository: IngredientRepository, menu_repository: MenuRepository):
        self.ingredient_repository = ingredient_repository
        self.menu_repository = menu_repository
    
    def check_availability(self, menu_item: MenuItem, quantity: int = 1) -> bool:
        """Check if enough ingredients are available for a menu item"""
        for ingredient_id, required_quantity in menu_item.ingredients.items():
            ingredient = self.ingredient_repository.get(ingredient_id)
            if not ingredient or ingredient.current_stock < (required_quantity * quantity):
                return False
        return True
    
    def consume_ingredients(self, menu_item: MenuItem, quantity: int = 1):
        """Consume ingredients for a menu item"""
        if not self.check_availability(menu_item, quantity):
            raise InventoryException(f"Insufficient ingredients for {menu_item.name}")
        
        for ingredient_id, required_quantity in menu_item.ingredients.items():
            consumed_quantity = required_quantity * quantity
            self.ingredient_repository.update_stock(ingredient_id, -consumed_quantity)
            
            # Log inventory transaction
            self._log_transaction(ingredient_id, -consumed_quantity, "consumption", f"Used for {menu_item.name}")
    
    def restock_ingredient(self, ingredient_id: str, quantity: Decimal, reason: str = "Restock"):
        """Restock an ingredient"""
        self.ingredient_repository.update_stock(ingredient_id, quantity)
        self._log_transaction(ingredient_id, quantity, "restock", reason)
    
    def get_low_stock_alerts(self) -> List[Ingredient]:
        """Get ingredients with low stock"""
        return self.ingredient_repository.get_low_stock()
    
    def _log_transaction(self, ingredient_id: str, quantity: Decimal, transaction_type: str, reason: str):
        """Log inventory transaction"""
        query = """
        INSERT INTO inventory_transactions (id, ingredient_id, quantity, transaction_type, reason, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """
        params = (str(uuid.uuid4()), ingredient_id, float(quantity), transaction_type, reason, datetime.datetime.now())
        
        db_manager = DatabaseManager()
        db_manager.execute_update(query, params)

# ==================== ORDER PROCESSING SERVICE ====================

class OrderProcessingService:
    """Service for processing orders"""
    
    def __init__(self, order_repository: OrderRepository, inventory_service: InventoryService):
        self.order_repository = order_repository
        self.inventory_service = inventory_service
        self._order_queue = queue.Queue()
        self._processing = False
    
    def place_order(self, order: Order) -> bool:
        """Place a new order"""
        try:
            # Validate order
            if not order.items:
                raise OrderException("Order must contain at least one item")
            
            # Check ingredient availability
            for item in order.items:
                menu_item = self._get_menu_item(item.menu_item_id)
                if not self.inventory_service.check_availability(menu_item, item.quantity):
                    raise InventoryException(f"Insufficient ingredients for {menu_item.name}")
            
            # Save order
            self.order_repository.add(order)
            
            # Add to processing queue
            self._order_queue.put(order.id)
            
            logger.info(f"Order {order.id} placed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to place order: {e}")
            return False
    
    def process_orders(self):
        """Process orders from the queue"""
        self._processing = True
        while self._processing:
            try:
                order_id = self._order_queue.get(timeout=1)
                self._process_single_order(order_id)
                self._order_queue.task_done()
            except queue.Empty:
                continue
    
    def _process_single_order(self, order_id: str):
        """Process a single order"""
        try:
            order = self.order_repository.get(order_id)
            if not order:
                logger.error(f"Order {order_id} not found")
                return
            
            # Update status to confirmed
            order.update_status(OrderStatus.CONFIRMED)
            self.order_repository.update(order)
            
            # Consume ingredients
            for item in order.items:
                menu_item = self._get_menu_item(item.menu_item_id)
                self.inventory_service.consume_ingredients(menu_item, item.quantity)
            
            # Update status to preparing
            order.update_status(OrderStatus.PREPARING)
            self.order_repository.update(order)
            
            # Simulate preparation time
            preparation_time = sum(self._get_menu_item(item.menu_item_id).preparation_time * item.quantity 
                                 for item in order.items)
            time.sleep(min(preparation_time, 5))  # Cap at 5 seconds for simulation
            
            # Update status to ready
            order.update_status(OrderStatus.READY)
            self.order_repository.update(order)
            
            logger.info(f"Order {order_id} processed successfully")
            
        except Exception as e:
            logger.error(f"Error processing order {order_id}: {e}")
            # Mark order as cancelled in case of error
            try:
                order.update_status(OrderStatus.CANCELLED)
                self.order_repository.update(order)
            except:
                pass
    
    def _get_menu_item(self, menu_item_id: str) -> MenuItem:
        """Get menu item (in a real system, this would use MenuRepository)"""
        # This is a simplified version - in reality, you'd inject MenuRepository
        db_manager = DatabaseManager()
        menu_repo = MenuRepository(db_manager)
        return menu_repo.get(menu_item_id)
    
    def stop_processing(self):
        """Stop order processing"""
        self._processing = False

# ==================== REPORTING AND ANALYTICS MODULE ====================

class ReportService:
    """Service for generating reports and analytics"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def get_sales_report(self, start_date: datetime.datetime, end_date: datetime.datetime) -> Dict:
        """Generate sales report for a date range"""
        query = """
        SELECT 
            DATE(created_at) as date,
            COUNT(*) as total_orders,
            SUM(total_amount) as total_revenue,
            AVG(total_amount) as average_order_value
        FROM orders 
        WHERE created_at BETWEEN ? AND ? AND status = 'paid'
        GROUP BY DATE(created_at)
        ORDER BY date
        """
        params = (start_date, end_date)
        results = self.db_manager.execute_query(query, params)
        
        return {
            'period': {'start': start_date, 'end': end_date},
            'daily_sales': [dict(row) for row in results],
            'summary': self._calculate_sales_summary(results)
        }
    
    def get_popular_items_report(self, start_date: datetime.datetime, end_date: datetime.datetime) -> List[Dict]:
        """Get report of most popular menu items"""
        query = """
        SELECT 
            mi.name,
            mi.category,
            COUNT(oi.id) as times_ordered,
            SUM(oi.quantity) as total_quantity,
            SUM(oi.quantity * oi.unit_price) as total_revenue
        FROM order_items oi
        JOIN menu_items mi ON oi.menu_item_id = mi.id
        JOIN orders o ON oi.order_id = o.id
        WHERE o.created_at BETWEEN ? AND ? AND o.status = 'paid'
        GROUP BY mi.id, mi.name, mi.category
        ORDER BY total_quantity DESC
        LIMIT 20
        """
        params = (start_date, end_date)
        results = self.db_manager.execute_query(query, params)
        return [dict(row) for row in results]
    
    def get_inventory_report(self) -> Dict:
        """Generate inventory report"""
        query = """
        SELECT 
            name,
            unit,
            current_stock,
            min_stock,
            unit_cost,
            (current_stock * unit_cost) as total_value
        FROM ingredients
        ORDER BY (current_stock < min_stock) DESC, current_stock ASC
        """
        results = self.db_manager.execute_query(query)
        
        low_stock_count = sum(1 for row in results if row['current_stock'] < row['min_stock'])
        total_value = sum(row['total_value'] for row in results)
        
        return {
            'inventory_items': [dict(row) for row in results],
            'low_stock_count': low_stock_count,
            'total_inventory_value': total_value
        }
    
    def _calculate_sales_summary(self, daily_sales) -> Dict:
        """Calculate summary statistics from daily sales"""
        if not daily_sales:
            return {}
        
        total_orders = sum(row['total_orders'] for row in daily_sales)
        total_revenue = sum(row['total_revenue'] for row in daily_sales)
        average_order_value = total_revenue / total_orders if total_orders > 0 else 0
        
        return {
            'total_orders': total_orders,
            'total_revenue': total_revenue,
            'average_order_value': average_order_value,
            'report_days': len(daily_sales)
        }

# ==================== NOTIFICATION SERVICE ====================

class NotificationService:
    """Service for sending notifications"""
    
    def __init__(self):
        self.observers = []
    
    def attach(self, observer):
        """Attach an observer"""
        self.observers.append(observer)
    
    def detach(self, observer):
        """Detach an observer"""
        self.observers.remove(observer)
    
    def notify(self, message: str, notification_type: str = "info"):
        """Notify all observers"""
        for observer in self.observers:
            observer.update(message, notification_type)

class NotificationObserver:
    """Base observer class for notifications"""
    
    def update(self, message: str, notification_type: str):
        pass

class LoggingNotificationObserver(NotificationObserver):
    """Observer that logs notifications"""
    
    def update(self, message: str, notification_type: str):
        log_method = getattr(logger, notification_type, logger.info)
        log_method(f"Notification: {message}")

class EmailNotificationObserver(NotificationObserver):
    """Observer that sends email notifications (simulated)"""
    
    def update(self, message: str, notification_type: str):
        # Simulate email sending
        if notification_type in ["error", "critical"]:
            print(f"[EMAIL] {notification_type.upper()}: {message}")

# ==================== MAIN APPLICATION CLASS ====================

class RestaurantManagementSystem:
    """Main application class coordinating all modules"""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self._initialize_repositories()
        self._initialize_services()
        self._setup_notifications()
        self._seed_sample_data()
    
    def _initialize_repositories(self):
        """Initialize all repositories"""
        self.user_repository = UserRepository(self.db_manager)
        self.menu_repository = MenuRepository(self.db_manager)
        self.ingredient_repository = IngredientRepository(self.db_manager)
        self.order_repository = OrderRepository(self.db_manager)
        self.payment_repository = PaymentRepository(self.db_manager)
        self.table_repository = TableRepository(self.db_manager)
    
    def _initialize_services(self):
        """Initialize all services"""
        self.auth_service = AuthenticationService(self.user_repository)
        self.inventory_service = InventoryService(self.ingredient_repository, self.menu_repository)
        self.order_processing_service = OrderProcessingService(self.order_repository, self.inventory_service)
        self.report_service = ReportService(self.db_manager)
        self.notification_service = NotificationService()
        
        # Start order processing in background thread
        self.processing_thread = threading.Thread(target=self.order_processing_service.process_orders, daemon=True)
        self.processing_thread.start()
    
    def _setup_notifications(self):
        """Setup notification observers"""
        self.notification_service.attach(LoggingNotificationObserver())
        self.notification_service.attach(EmailNotificationObserver())
    
    def _seed_sample_data(self):
        """Seed the database with sample data"""
        try:
            # Check if data already exists
            if self.user_repository.get_all():
                return
            
            self._create_sample_users()
            self._create_sample_ingredients()
            self._create_sample_menu_items()
            self._create_sample_tables()
            
            logger.info("Sample data seeded successfully")
        except Exception as e:
            logger.error(f"Error seeding sample data: {e}")
    
    def _create_sample_users(self):
        """Create sample users"""
        sample_users = [
            User(username="admin", email="admin@restaurant.com", role=UserRole.ADMIN, 
                 first_name="System", last_name="Administrator"),
            User(username="manager", email="manager@restaurant.com", role=UserRole.MANAGER,
                 first_name="John", last_name="Manager"),
            User(username="chef", email="chef@restaurant.com", role=UserRole.CHEF,
                 first_name="Gordon", last_name="Ramsay"),
            User(username="waiter1", email="waiter1@restaurant.com", role=UserRole.WAITER,
                 first_name="Alice", last_name="Johnson"),
            User(username="customer1", email="customer1@example.com", role=UserRole.CUSTOMER,
                 first_name="Bob", last_name="Smith")
        ]
        
        for user in sample_users:
            user.set_password("password123")
            self.user_repository.add(user)
    
    def _create_sample_ingredients(self):
        """Create sample ingredients"""
        sample_ingredients = [
            Ingredient(name="Flour", unit="kg", current_stock=Decimal('50'), min_stock=Decimal('10'), unit_cost=Decimal('0.5')),
            Ingredient(name="Sugar", unit="kg", current_stock=Decimal('30'), min_stock=Decimal('5'), unit_cost=Decimal('0.8')),
            Ingredient(name="Butter", unit="kg", current_stock=Decimal('20'), min_stock=Decimal('3'), unit_cost=Decimal('5.0')),
            Ingredient(name="Eggs", unit="pieces", current_stock=Decimal('200'), min_stock=Decimal('50'), unit_cost=Decimal('0.3')),
            Ingredient(name="Milk", unit="liter", current_stock=Decimal('40'), min_stock=Decimal('10'), unit_cost=Decimal('1.2')),
            Ingredient(name="Beef", unit="kg", current_stock=Decimal('25'), min_stock=Decimal('5'), unit_cost=Decimal('15.0')),
            Ingredient(name="Chicken", unit="kg", current_stock=Decimal('20'), min_stock=Decimal('4'), unit_cost=Decimal('12.0')),
            Ingredient(name="Rice", unit="kg", current_stock=Decimal('40'), min_stock=Decimal('8'), unit_cost=Decimal('2.0')),
            Ingredient(name="Tomato", unit="kg", current_stock=Decimal('15'), min_stock=Decimal('3'), unit_cost=Decimal('3.0')),
            Ingredient(name="Lettuce", unit="kg", current_stock=Decimal('10'), min_stock=Decimal('2'), unit_cost=Decimal('2.5'))
        ]
        
        for ingredient in sample_ingredients:
            self.ingredient_repository.add(ingredient)
    
    def _create_sample_menu_items(self):
        """Create sample menu items"""
        # Get ingredient IDs
        ingredients = self.ingredient_repository.get_all()
        ingredient_map = {ing.name: ing.id for ing in ingredients}
        
        sample_menu_items = [
            MenuItem(
                name="Cheeseburger", 
                description="Juicy beef patty with cheese, lettuce, and tomato",
                category="Main Course",
                price=Decimal('12.99'),
                cost=Decimal('4.50'),
                preparation_time=15,
                calories=550,
                ingredients={
                    ingredient_map["Beef"]: Decimal('0.2'),
                    ingredient_map["Lettuce"]: Decimal('0.05'),
                    ingredient_map["Tomato"]: Decimal('0.05')
                }
            ),
            MenuItem(
                name="Caesar Salad",
                description="Fresh romaine lettuce with Caesar dressing and croutons",
                category="Main Course",
                price=Decimal('9.99'),
                cost=Decimal('3.20'),
                preparation_time=10,
                calories=320,
                ingredients={
                    ingredient_map["Lettuce"]: Decimal('0.15'),
                    ingredient_map["Tomato"]: Decimal('0.08')
                }
            ),
            MenuItem(
                name="Chocolate Cake",
                description="Rich chocolate cake with chocolate frosting",
                category="Desserts",
                price=Decimal('6.99'),
                cost=Decimal('1.80'),
                preparation_time=5,
                calories=450,
                ingredients={
                    ingredient_map["Flour"]: Decimal('0.1'),
                    ingredient_map["Sugar"]: Decimal('0.08'),
                    ingredient_map["Butter"]: Decimal('0.05'),
                    ingredient_map["Eggs"]: Decimal('2')
                }
            )
        ]
        
        for item in sample_menu_items:
            self.menu_repository.add(item)
    
    def _create_sample_tables(self):
        """Create sample tables"""
        for i in range(1, 11):
            table = Table(
                table_number=i,
                capacity=4 if i <= 8 else 6,  # Larger tables for last 2
                location="Main Hall" if i <= 6 else "Terrace"
            )
            self.table_repository.add(table)
    
    def login(self, username: str, password: str) -> bool:
        """Login user"""
        return self.auth_service.login(username, password)
    
    def logout(self):
        """Logout current user"""
        self.auth_service.logout()
    
    def get_current_user(self) -> Optional[User]:
        """Get current user"""
        return self.auth_service.get_current_user()
    
    def has_permission(self, required_role: UserRole) -> bool:
        """Check if current user has permission"""
        return self.auth_service.has_permission(required_role)
    
    def create_order(self, table_number: int, items: List[Tuple[str, int]]) -> Optional[Order]:
        """Create a new order"""
        if not self.has_permission(UserRole.WAITER):
            raise RestaurantException("Insufficient permissions to create order")
        
        try:
            # Get table
            table = self.table_repository.get_by_number(table_number)
            if not table:
                raise OrderException(f"Table {table_number} not found")
            
            if table.is_occupied:
                raise OrderException(f"Table {table_number} is already occupied")
            
            # Create order
            order = Order()
            order.table_id = table.id
            order.waiter_id = self.get_current_user().id
            
            # Add items to order
            for menu_item_name, quantity in items:
                menu_items = self.menu_repository.get_all()
                menu_item = next((item for item in menu_items if item.name == menu_item_name), None)
                if not menu_item:
                    raise OrderException(f"Menu item {menu_item_name} not found")
                
                if not menu_item.is_available:
                    raise OrderException(f"Menu item {menu_item_name} is not available")
                
                order.add_item(menu_item, quantity)
            
            # Occupy table
            table.occupy()
            self.table_repository.update(table)
            
            # Place order
            if self.order_processing_service.place_order(order):
                self.notification_service.notify(f"New order created: {order.id}", "info")
                return order
            
            return None
            
        except Exception as e:
            logger.error(f"Error creating order: {e}")
            self.notification_service.notify(f"Failed to create order: {e}", "error")
            raise
    
    def process_payment(self, order_id: str, payment_method: PaymentMethod, tip_amount: Decimal = Decimal('0')) -> bool:
        """Process payment for an order"""
        try:
            order = self.order_repository.get(order_id)
            if not order:
                raise PaymentException(f"Order {order_id} not found")
            
            if order.status != OrderStatus.SERVED:
                raise PaymentException("Order must be served before payment")
            
            # Create payment
            payment = Payment()
            payment.order_id = order_id
            payment.amount = order.total_amount
            payment.payment_method = payment_method
            payment.tip_amount = tip_amount
            
            # Process payment
            if payment.process_payment():
                self.payment_repository.add(payment)
                
                # Update order status
                order.update_status(OrderStatus.PAID)
                self.order_repository.update(order)
                
                # Vacate table
                table = self.table_repository.get(order.table_id)
                if table:
                    table.vacate()
                    self.table_repository.update(table)
                
                self.notification_service.notify(f"Payment processed for order {order_id}", "info")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error processing payment: {e}")
            self.notification_service.notify(f"Payment failed: {e}", "error")
            return False
    
    def generate_daily_report(self) -> Dict:
        """Generate daily sales report"""
        if not self.has_permission(UserRole.MANAGER):
            raise RestaurantException("Insufficient permissions to generate reports")
        
        end_date = datetime.datetime.now()
        start_date = end_date - datetime.timedelta(days=1)
        
        return self.report_service.get_sales_report(start_date, end_date)
    
    def get_low_stock_alerts(self) -> List[Ingredient]:
        """Get low stock alerts"""
        return self.inventory_service.get_low_stock_alerts()
    
    def shutdown(self):
        """Shutdown the system gracefully"""
        logger.info("Shutting down restaurant management system...")
        self.order_processing_service.stop_processing()
        self.processing_thread.join(timeout=5)
        logger.info("System shutdown complete")

# ==================== COMMAND LINE INTERFACE ====================

class RestaurantCLI:
    """Command Line Interface for the Restaurant Management System"""
    
    def __init__(self):
        self.system = RestaurantManagementSystem()
        self.is_running = False
    
    def print_menu(self):
        """Print main menu"""
        print("\n" + "="*50)
        print("    RESTAURANT MANAGEMENT SYSTEM")
        print("="*50)
        print("1. Login")
        print("2. View Menu")
        print("3. Create Order")
        print("4. View Orders")
        print("5. Process Payment")
        print("6. View Reports")
        print("7. Manage Inventory")
        print("8. Logout")
        print("9. Exit")
        print("="*50)
    
    def run(self):
        """Run the CLI"""
        self.is_running = True
        print("Welcome to the Restaurant Management System!")
        
        while self.is_running:
            self.print_menu()
            choice = input("Enter your choice (1-9): ").strip()
            
            try:
                if choice == "1":
                    self.handle_login()
                elif choice == "2":
                    self.handle_view_menu()
                elif choice == "3":
                    self.handle_create_order()
                elif choice == "4":
                    self.handle_view_orders()
                elif choice == "5":
                    self.handle_process_payment()
                elif choice == "6":
                    self.handle_view_reports()
                elif choice == "7":
                    self.handle_manage_inventory()
                elif choice == "8":
                    self.handle_logout()
                elif choice == "9":
                    self.handle_exit()
                else:
                    print("Invalid choice. Please try again.")
            except Exception as e:
                print(f"Error: {e}")
    
    def handle_login(self):
        """Handle user login"""
        if self.system.get_current_user():
            print("You are already logged in.")
            return
        
        username = input("Username: ").strip()
        password = input("Password: ").strip()
        
        if self.system.login(username, password):
            user = self.system.get_current_user()
            print(f"Welcome, {user.get_full_name()}!")
        else:
            print("Invalid username or password.")
    
    def handle_view_menu(self):
        """Handle menu viewing"""
        menu_items = self.system.menu_repository.get_all()
        
        print("\n" + "="*50)
        print("                 MENU")
        print("="*50)
        
        for category in Config.CATEGORIES:
            category_items = [item for item in menu_items if item.category == category and item.is_available]
            if category_items:
                print(f"\n{category.upper()}:")
                print("-" * 30)
                for item in category_items:
                    print(f"  {item.name:20} ${item.price:6.2f}")
                    if item.description:
                        print(f"    {item.description}")
    
    def handle_create_order(self):
        """Handle order creation"""
        if not self.system.get_current_user():
            print("Please login first.")
            return
        
        try:
            # Get table number
            table_number = int(input("Enter table number: "))
            
            # Display available menu items
            menu_items = self.system.menu_repository.get_all()
            available_items = [item for item in menu_items if item.is_available]
            
            print("\nAvailable Menu Items:")
            for i, item in enumerate(available_items, 1):
                print(f"{i}. {item.name} - ${item.price:.2f}")
            
            # Get order items
            order_items = []
            while True:
                try:
                    choice = input("Enter item number (or 'done' to finish): ").strip()
                    if choice.lower() == 'done':
                        break
                    
                    item_index = int(choice) - 1
                    if 0 <= item_index < len(available_items):
                        quantity = int(input("Enter quantity: "))
                        order_items.append((available_items[item_index].name, quantity))
                    else:
                        print("Invalid item number.")
                except ValueError:
                    print("Please enter a valid number.")
            
            if not order_items:
                print("No items selected.")
                return
            
            # Create order
            order = self.system.create_order(table_number, order_items)
            if order:
                print(f"Order created successfully! Order ID: {order.id}")
                print(f"Total amount: ${order.total_amount:.2f}")
            else:
                print("Failed to create order.")
                
        except Exception as e:
            print(f"Error creating order: {e}")
    
    def handle_view_orders(self):
        """Handle order viewing"""
        if not self.system.get_current_user():
            print("Please login first.")
            return
        
        orders = self.system.order_repository.get_all()
        
        print("\n" + "="*50)
        print("                 ORDERS")
        print("="*50)
        
        for order in orders:
            print(f"\nOrder ID: {order.id}")
            print(f"Table: {order.table_id} | Status: {order.status.value}")
            print(f"Total: ${order.total_amount:.2f} | Created: {order.created_at.strftime('%Y-%m-%d %H:%M')}")
            print("Items:")
            for item in order.items:
                print(f"  - {item.quantity}x (Item ID: {item.menu_item_id})")
    
    def handle_process_payment(self):
        """Handle payment processing"""
        if not self.system.get_current_user():
            print("Please login first.")
            return
        
        try:
            order_id = input("Enter order ID: ").strip()
            
            print("Payment Methods:")
            for i, method in enumerate(PaymentMethod, 1):
                print(f"{i}. {method.value}")
            
            method_choice = int(input("Select payment method: ")) - 1
            if 0 <= method_choice < len(list(PaymentMethod)):
                payment_method = list(PaymentMethod)[method_choice]
            else:
                print("Invalid payment method.")
                return
            
            tip_amount = Decimal(input("Enter tip amount (0 for no tip): ").strip() or "0")
            
            if self.system.process_payment(order_id, payment_method, tip_amount):
                print("Payment processed successfully!")
            else:
                print("Payment failed.")
                
        except Exception as e:
            print(f"Error processing payment: {e}")
    
    def handle_view_reports(self):
        """Handle report viewing"""
        if not self.system.get_current_user():
            print("Please login first.")
            return
        
        if not self.system.has_permission(UserRole.MANAGER):
            print("Insufficient permissions to view reports.")
            return
        
        try:
            report = self.system.generate_daily_report()
            print("\nDaily Sales Report:")
            print(json.dumps(report, indent=2, default=str))
            
            low_stock = self.system.get_low_stock_alerts()
            if low_stock:
                print("\nLow Stock Alerts:")
                for item in low_stock:
                    print(f"  - {item.name}: {item.current_stock} {item.unit} (min: {item.min_stock})")
                    
        except Exception as e:
            print(f"Error generating reports: {e}")
    
    def handle_manage_inventory(self):
        """Handle inventory management"""
        if not self.system.get_current_user():
            print("Please login first.")
            return
        
        if not self.system.has_permission(UserRole.MANAGER):
            print("Insufficient permissions to manage inventory.")
            return
        
        print("\nInventory Management:")
        print("1. View Inventory")
        print("2. Restock Item")
        
        choice = input("Enter choice: ").strip()
        
        if choice == "1":
            ingredients = self.system.ingredient_repository.get_all()
            print("\nCurrent Inventory:")
            for ing in ingredients:
                status = "LOW STOCK" if ing.is_low_stock() else "OK"
                print(f"  {ing.name:15} {ing.current_stock:6.1f} {ing.unit:5} (min: {ing.min_stock}) [{status}]")
        
        elif choice == "2":
            ingredient_id = input("Enter ingredient ID: ").strip()
            quantity = Decimal(input("Enter quantity to add: ").strip())
            reason = input("Enter reason for restock: ").strip()
            
            self.system.inventory_service.restock_ingredient(ingredient_id, quantity, reason)
            print("Ingredient restocked successfully!")
    
    def handle_logout(self):
        """Handle user logout"""
        if self.system.get_current_user():
            self.system.logout()
            print("Logged out successfully.")
        else:
            print("No user is currently logged in.")
    
    def handle_exit(self):
        """Handle application exit"""
        print("Thank you for using the Restaurant Management System!")
        self.system.shutdown()
        self.is_running = False

# ==================== TESTING MODULE ====================

import unittest

class TestRestaurantSystem(unittest.TestCase):
    """Test cases for the restaurant management system"""
    
    def setUp(self):
        """Set up test environment"""
        self.system = RestaurantManagementSystem()
        # Use in-memory database for testing
        self.system.db_manager.connection = sqlite3.connect(':memory:')
        self.system.db_manager._create_tables()
    
    def test_user_authentication(self):
        """Test user authentication"""
        # Create test user
        user = User(username="testuser", email="test@example.com", role=UserRole.CUSTOMER)
        user.set_password("testpass")
        self.system.user_repository.add(user)
        
        # Test successful login
        self.assertTrue(self.system.login("testuser", "testpass"))
        self.assertIsNotNone(self.system.get_current_user())
        
        # Test failed login
        self.system.logout()
        self.assertFalse(self.system.login("testuser", "wrongpass"))
    
    def test_order_creation(self):
        """Test order creation"""
        # Login as waiter
        waiter = User(username="testwaiter", email="waiter@test.com", role=UserRole.WAITER)
        waiter.set_password("pass")
        self.system.user_repository.add(waiter)
        self.system.login("testwaiter", "pass")
        
        # Create test table
        table = Table(table_number=99, capacity=4)
        self.system.table_repository.add(table)
        
        # Create test menu item
        menu_item = MenuItem(name="Test Item", category="Main Course", price=Decimal('10.00'))
        self.system.menu_repository.add(menu_item)
        
        # Test order creation
        order = self.system.create_order(99, [("Test Item", 2)])
        self.assertIsNotNone(order)
        self.assertEqual(order.total_amount, Decimal('21.60'))  # 20 + tax
    
    def test_inventory_management(self):
        """Test inventory management"""
        # Create test ingredient
        ingredient = Ingredient(name="Test Ingredient", unit="kg", current_stock=Decimal('10'), min_stock=Decimal('2'))
        self.system.ingredient_repository.add(ingredient)
        
        # Test low stock detection
        low_stock = self.system.get_low_stock_alerts()
        self.assertEqual(len(low_stock), 0)  # Should not be low stock
        
        # Update to low stock
        self.system.ingredient_repository.update_stock(ingredient.id, Decimal('-9'))
        low_stock = self.system.get_low_stock_alerts()
        self.assertEqual(len(low_stock), 1)  # Should be low stock
    
    def tearDown(self):
        """Clean up after tests"""
        self.system.shutdown()

# ==================== ASYNCHRONOUS TASKS MODULE ====================

class AsyncTaskManager:
    """Manager for asynchronous tasks"""
    
    def __init__(self):
        self.tasks = []
    
    async def send_email_notification(self, to_email: str, subject: str, body: str):
        """Send email notification asynchronously (simulated)"""
        await asyncio.sleep(1)  # Simulate network delay
        print(f"[ASYNC EMAIL] To: {to_email}, Subject: {subject}")
        return True
    
    async def backup_database(self):
        """Backup database asynchronously"""
        await asyncio.sleep(2)  # Simulate backup process
        print("[ASYNC BACKUP] Database backup completed")
        return True
    
    async def process_batch_orders(self, orders: List[Order]):
        """Process multiple orders asynchronously"""
        tasks = [self._process_single_order_async(order) for order in orders]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results
    
    async def _process_single_order_async(self, order: Order):
        """Process single order asynchronously"""
        await asyncio.sleep(0.5)  # Simulate processing time
        return f"Order {order.id} processed"

# ==================== DATA EXPORT MODULE ====================

class DataExporter:
    """Handles data export to various formats"""
    
    def __init__(self, system: RestaurantManagementSystem):
        self.system = system
    
    def export_orders_to_csv(self, filename: str, start_date: datetime.datetime, end_date: datetime.datetime):
        """Export orders to CSV"""
        orders = self.system.order_repository.get_all()
        filtered_orders = [order for order in orders if start_date <= order.created_at <= end_date]
        
        with open(filename, 'w', newline='') as csvfile:
            fieldnames = ['order_id', 'table_id', 'status', 'total_amount', 'created_at']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for order in filtered_orders:
                writer.writerow({
                    'order_id': order.id,
                    'table_id': order.table_id,
                    'status': order.status.value,
                    'total_amount': float(order.total_amount),
                    'created_at': order.created_at.isoformat()
                })
    
    def export_menu_to_json(self, filename: str):
        """Export menu to JSON"""
        menu_items = self.system.menu_repository.get_all()
        
        menu_data = {
            'export_date': datetime.datetime.now().isoformat(),
            'menu_items': [item.to_dict() for item in menu_items]
        }
        
        with open(filename, 'w') as jsonfile:
            json.dump(menu_data, jsonfile, indent=2)
    
    def export_inventory_report(self, filename: str):
        """Export inventory report"""
        report = self.system.report_service.get_inventory_report()
        
        with open(filename, 'w') as file:
            file.write("INVENTORY REPORT\n")
            file.write("=" * 50 + "\n")
            file.write(f"Generated: {datetime.datetime.now()}\n")
            file.write(f"Total Value: ${report['total_inventory_value']:.2f}\n")
            file.write(f"Low Stock Items: {report['low_stock_count']}\n\n")
            
            file.write("ITEMS:\n")
            file.write("-" * 50 + "\n")
            for item in report['inventory_items']:
                status = "LOW STOCK" if item['current_stock'] < item['min_stock'] else "OK"
                file.write(f"{item['name']:15} {item['current_stock']:6.1f} {item['unit']:5} ")
                file.write(f"${item['total_value']:6.2f} [{status}]\n")

# ==================== CACHE MANAGEMENT MODULE ====================

class CacheManager:
    """Manages caching for frequently accessed data"""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.cache = {}
        self.access_times = {}
    
    def get(self, key: str):
        """Get value from cache"""
        if key in self.cache:
            self.access_times[key] = time.time()
            return self.cache[key]
        return None
    
    def set(self, key: str, value, ttl: int = 300):
        """Set value in cache with TTL"""
        if len(self.cache) >= self.max_size:
            self._evict_oldest()
        
        self.cache[key] = value
        self.access_times[key] = time.time()
    
    def _evict_oldest(self):
        """Evict oldest accessed item"""
        if not self.access_times:
            return
        
        oldest_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
        del self.cache[oldest_key]
        del self.access_times[oldest_key]
    
    def clear(self):
        """Clear entire cache"""
        self.cache.clear()
        self.access_times.clear()

# ==================== MAIN EXECUTION ====================

def main():
    """Main execution function"""
    try:
        # Run tests if requested
        if len(sys.argv) > 1 and sys.argv[1] == "test":
            print("Running tests...")
            unittest.main(argv=[''], verbosity=2, exit=False)
            return
        
        # Start CLI
        cli = RestaurantCLI()
        cli.run()
        
    except KeyboardInterrupt:
        print("\n\nApplication interrupted by user.")
    except Exception as e:
        print(f"Unexpected error: {e}")
        logger.critical(f"Application crash: {e}", exc_info=True)

if __name__ == "__main__":
    import sys
    main()