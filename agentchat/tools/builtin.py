"""Built-in tools for the agent chat application."""

from typing import Any

from langchain_core.tools import tool

from .registry import register_tool
from .skills import get_skill, search_skills


@tool
def query_sales(region: str) -> dict[str, Any]:
    """Query sales data for a region.

    Args:
        region: The region name (west, east, central, north, south).

    Returns: {"region": str, "revenue": int, "units": int, "top_product": str}
    Error: {"error": str} if region not found.
    """
    data: dict[str, dict[str, Any]] = {
        "west": {"revenue": 150000, "units": 1200, "top_product": "Widget A"},
        "east": {"revenue": 220000, "units": 1800, "top_product": "Widget B"},
        "central": {"revenue": 180000, "units": 1500, "top_product": "Widget A"},
        "north": {"revenue": 95000, "units": 800, "top_product": "Widget C"},
        "south": {"revenue": 130000, "units": 1100, "top_product": "Widget B"},
    }
    region_lower = region.lower()
    if region_lower in data:
        return {"region": region, **data[region_lower]}
    return {"error": f"Unknown region: {region}"}


@tool
def get_weather(city: str) -> dict[str, Any]:
    """Get current weather for a city.

    Args:
        city: The city name.

    Returns: {"city": str, "temp": int, "condition": str, "humidity": int}
    Error: {"error": str} if city not found.
    """
    data: dict[str, dict[str, Any]] = {
        "tokyo": {"temp": 22, "condition": "Sunny", "humidity": 45},
        "new york": {"temp": 18, "condition": "Cloudy", "humidity": 60},
        "london": {"temp": 15, "condition": "Rainy", "humidity": 80},
        "paris": {"temp": 20, "condition": "Partly Cloudy", "humidity": 55},
        "sydney": {"temp": 25, "condition": "Sunny", "humidity": 40},
    }
    city_lower = city.lower()
    if city_lower in data:
        return {"city": city, **data[city_lower]}
    return {"error": f"Unknown city: {city}"}


@tool
def send_email(to: str, subject: str, body: str) -> dict[str, Any]:
    """Send an email to a recipient.

    Args:
        to: Email address of the recipient.
        subject: Email subject line.
        body: Email body content.

    Returns: {"status": str, "to": str, "subject": str, "body_length": int}
    """
    return {
        "status": "sent",
        "to": to,
        "subject": subject,
        "body_length": len(body),
    }


@tool
def create_calendar_event(title: str, date: str, time: str = "09:00") -> dict[str, Any]:
    """Create a calendar event.

    Args:
        title: Event title.
        date: Event date (YYYY-MM-DD format).
        time: Event time (HH:MM format, default 09:00).

    Returns: {"status": str, "title": str, "date": str, "time": str}
    """
    return {
        "status": "created",
        "title": title,
        "date": date,
        "time": time,
    }


@tool
def list_calendar_events(date: str) -> dict[str, Any]:
    """List calendar events for a specific date.

    Args:
        date: The date to query (YYYY-MM-DD format).

    Returns: {"date": str, "events": [{"time": str, "title": str}, ...]}
    """
    return {
        "date": date,
        "events": [
            {"time": "10:00", "title": "Team Meeting"},
            {"time": "12:00", "title": "Lunch"},
            {"time": "14:00", "title": "Project Review"},
        ],
    }


@tool
def read_emails(folder: str = "inbox") -> dict[str, Any]:
    """Read emails from a folder.

    Args:
        folder: The folder name (default: inbox).

    Returns: {"folder": str, "count": int, "emails": [{"from": str, "subject": str, "unread": bool}, ...]}
    """
    return {
        "folder": folder,
        "count": 3,
        "emails": [
            {"from": "boss@company.com", "subject": "Q4 Review", "unread": True},
            {"from": "team@company.com", "subject": "Meeting Notes", "unread": False},
            {"from": "hr@company.com", "subject": "Holiday Schedule", "unread": True},
        ],
    }


def register_builtin_tools() -> None:
    """Register all built-in tools in the global registry."""
    for t in [
        query_sales,
        get_weather,
        send_email,
        create_calendar_event,
        list_calendar_events,
        read_emails,
        search_skills,
        get_skill,
    ]:
        register_tool(t)
