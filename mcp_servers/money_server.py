"""Money domain MCP server: finance, shopping."""

from typing import Any

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Money")

# === Finance ===


@mcp.tool(name="finance__check_balance")
def check_balance(account: str = "checking") -> dict[str, Any]:
    """Check account balance.

    Args:
        account: Account type (checking, savings, credit).

    Returns: {"account": str, "balance": float, "currency": str}
    """
    balances = {"checking": 5432.10, "savings": 12500.00, "credit": -1250.50}
    return {"account": account, "balance": balances.get(account, 0), "currency": "USD"}


@mcp.tool(name="finance__transfer_money")
def transfer_money(from_account: str, to_account: str, amount: float) -> dict[str, Any]:
    """Transfer money between accounts.

    Args:
        from_account: Source account.
        to_account: Destination account.
        amount: Amount to transfer.

    Returns: {"success": True, "from": str, "to": str, "amount": float, "reference": str}
    """
    return {
        "success": True,
        "from": from_account,
        "to": to_account,
        "amount": amount,
        "reference": "TXN-2024-001234",
    }


@mcp.tool(name="finance__pay_bill")
def pay_bill(biller: str, amount: float, account: str = "checking") -> dict[str, Any]:
    """Pay a bill.

    Args:
        biller: Name of the biller.
        amount: Amount to pay.
        account: Account to pay from.

    Returns: {"success": True, "biller": str, "amount": float, "confirmation": str}
    """
    return {"success": True, "biller": biller, "amount": amount, "confirmation": "PAY-2024-005678"}


@mcp.tool(name="finance__get_transactions")
def get_transactions(account: str = "checking", days: int = 30) -> dict[str, Any]:
    """Get recent transactions.

    Args:
        account: Account to query.
        days: Number of days to look back.

    Returns: {"account": str, "transactions": [{"date": str, "description": str, "amount": float}]}
    """
    return {
        "account": account,
        "transactions": [
            {"date": "2024-01-15", "description": "Grocery Store", "amount": -85.50},
            {"date": "2024-01-14", "description": "Salary Deposit", "amount": 3500.00},
            {"date": "2024-01-13", "description": "Electric Bill", "amount": -120.00},
        ],
    }


@mcp.tool(name="finance__set_budget")
def set_budget(category: str, amount: float, period: str = "monthly") -> dict[str, Any]:
    """Set a spending budget.

    Args:
        category: Budget category (food, transport, entertainment, etc).
        amount: Budget amount.
        period: Time period (weekly, monthly).

    Returns: {"set": True, "category": str, "amount": float, "period": str}
    """
    return {"set": True, "category": category, "amount": amount, "period": period}


@mcp.tool(name="finance__get_stock_price")
def get_stock_price(symbol: str) -> dict[str, Any]:
    """Get current stock price.

    Args:
        symbol: Stock ticker symbol (e.g., AAPL, GOOGL).

    Returns: {"symbol": str, "price": float, "change": float, "change_percent": float}
    """
    prices = {"AAPL": 185.50, "GOOGL": 142.30, "MSFT": 378.20, "AMZN": 155.80}
    price = prices.get(symbol.upper(), 100.00)
    change = 2.50
    return {"symbol": symbol, "price": price, "change": change, "change_percent": round(change / price * 100, 2)}


@mcp.tool(name="finance__calculate_loan")
def calculate_loan(principal: float, rate: float, years: int) -> dict[str, Any]:
    """Calculate loan monthly payment.

    Args:
        principal: Loan amount.
        rate: Annual interest rate (percentage).
        years: Loan term in years.

    Returns: {"principal": float, "monthly_payment": float, "total_interest": float}
    """
    monthly_rate = rate / 100 / 12
    n_payments = years * 12
    if monthly_rate > 0:
        payment = principal * (monthly_rate * (1 + monthly_rate) ** n_payments) / ((1 + monthly_rate) ** n_payments - 1)
    else:
        payment = principal / n_payments
    total = payment * n_payments
    return {"principal": principal, "monthly_payment": round(payment, 2), "total_interest": round(total - principal, 2)}


# === Shopping ===


@mcp.tool(name="shopping__search_products")
def search_products(query: str, max_price: float = 0) -> dict[str, Any]:
    """Search for products.

    Args:
        query: Product search query.
        max_price: Maximum price filter (0 for no limit).

    Returns: {"products": [{"name": str, "price": float, "rating": float}]}
    """
    products = [
        {"name": f"{query} Pro", "price": 299.99, "rating": 4.5},
        {"name": f"{query} Standard", "price": 149.99, "rating": 4.2},
        {"name": f"{query} Basic", "price": 79.99, "rating": 3.9},
    ]
    if max_price > 0:
        products = [p for p in products if isinstance(p["price"], (int, float)) and p["price"] <= max_price]
    return {"query": query, "products": products}


@mcp.tool(name="shopping__compare_prices")
def compare_prices(product: str) -> dict[str, Any]:
    """Compare prices across stores.

    Args:
        product: Product name.

    Returns: {"product": str, "prices": [{"store": str, "price": float, "in_stock": bool}]}
    """
    return {
        "product": product,
        "prices": [
            {"store": "Amazon", "price": 149.99, "in_stock": True},
            {"store": "Best Buy", "price": 159.99, "in_stock": True},
            {"store": "Walmart", "price": 144.99, "in_stock": False},
        ],
    }


@mcp.tool(name="shopping__check_inventory")
def check_inventory(product: str, store: str) -> dict[str, Any]:
    """Check product availability at a store.

    Args:
        product: Product name.
        store: Store name or location.

    Returns: {"product": str, "store": str, "in_stock": bool, "quantity": int}
    """
    return {"product": product, "store": store, "in_stock": True, "quantity": 5}


@mcp.tool(name="shopping__track_order")
def track_order(order_id: str) -> dict[str, Any]:
    """Track an order.

    Args:
        order_id: Order ID number.

    Returns: {"order_id": str, "status": str, "location": str, "eta": str}
    """
    return {"order_id": order_id, "status": "In Transit", "location": "Local Distribution Center", "eta": "Tomorrow"}


@mcp.tool(name="shopping__add_to_cart")
def add_to_cart(product: str, quantity: int = 1) -> dict[str, Any]:
    """Add item to shopping cart.

    Args:
        product: Product name.
        quantity: Number of items to add.

    Returns: {"added": True, "product": str, "quantity": int, "cart_total": int}
    """
    return {"added": True, "product": product, "quantity": quantity, "cart_total": 3}


@mcp.tool(name="shopping__apply_coupon")
def apply_coupon(code: str) -> dict[str, Any]:
    """Apply a coupon code.

    Args:
        code: Coupon code.

    Returns: {"valid": bool, "discount": str, "code": str}
    """
    coupons = {"SAVE10": "10%", "SAVE20": "20%", "FREESHIP": "Free Shipping"}
    discount = coupons.get(code.upper())
    return {"valid": discount is not None, "discount": discount or "Invalid code", "code": code}


@mcp.tool(name="shopping__get_reviews")
def get_reviews(product: str, count: int = 5) -> dict[str, Any]:
    """Get product reviews.

    Args:
        product: Product name.
        count: Number of reviews to return.

    Returns: {"product": str, "avg_rating": float, "reviews": [{"rating": int, "comment": str}]}
    """
    reviews = [
        {"rating": 5, "comment": "Excellent product!"},
        {"rating": 4, "comment": "Good value for money"},
        {"rating": 5, "comment": "Highly recommend"},
    ]
    return {"product": product, "avg_rating": 4.5, "reviews": reviews[:count]}


if __name__ == "__main__":
    mcp.run(transport="stdio")
