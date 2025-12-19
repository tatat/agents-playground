"""Work domain MCP server: productivity, social, utilities, math, string."""

from typing import Any

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Work")

# === Math ===


@mcp.tool(name="math__add")
def add(a: int, b: int) -> dict[str, int]:
    """Add two numbers.

    Args:
        a: First number.
        b: Second number.

    Returns: {"result": int} where result is the sum of a and b.
    """
    return {"result": a + b}


@mcp.tool(name="math__multiply")
def multiply(a: int, b: int) -> dict[str, int]:
    """Multiply two numbers.

    Args:
        a: First number.
        b: Second number.

    Returns: {"result": int} where result is the product of a and b.
    """
    return {"result": a * b}


# === String ===


@mcp.tool(name="string__uppercase")
def uppercase(text: str) -> dict[str, str]:
    """Convert text to uppercase.

    Args:
        text: Input text to convert.

    Returns: {"result": str} where result is the uppercase version of text.
    """
    return {"result": text.upper()}


@mcp.tool(name="string__reverse")
def reverse(text: str) -> dict[str, str]:
    """Reverse a string.

    Args:
        text: Input text to reverse.

    Returns: {"result": str} where result is the reversed text.
    """
    return {"result": text[::-1]}


# === Productivity ===


@mcp.tool(name="productivity__create_task")
def create_task(title: str, due_date: str = "", priority: str = "medium") -> dict[str, Any]:
    """Create a new task.

    Args:
        title: Task title.
        due_date: Due date (YYYY-MM-DD).
        priority: Priority level (low, medium, high).

    Returns: {"created": True, "task_id": str, "title": str}
    """
    return {"created": True, "task_id": "TASK-001", "title": title, "priority": priority}


@mcp.tool(name="productivity__list_tasks")
def list_tasks(status: str = "pending", project: str = "") -> dict[str, Any]:
    """List tasks.

    Args:
        status: Task status (pending, in_progress, completed, all).
        project: Filter by project name.

    Returns: {"tasks": [{"id": str, "title": str, "status": str, "due": str}]}
    """
    tasks = [
        {"id": "TASK-001", "title": "Review proposal", "status": "pending", "due": "2024-01-20"},
        {"id": "TASK-002", "title": "Team meeting prep", "status": "in_progress", "due": "2024-01-18"},
        {"id": "TASK-003", "title": "Update documentation", "status": "pending", "due": "2024-01-22"},
    ]
    if status != "all":
        tasks = [t for t in tasks if t["status"] == status]
    return {"tasks": tasks}


@mcp.tool(name="productivity__create_event")
def create_event(title: str, date: str, time: str, duration: int = 60) -> dict[str, Any]:
    """Create a calendar event.

    Args:
        title: Event title.
        date: Event date (YYYY-MM-DD).
        time: Start time (HH:MM).
        duration: Duration in minutes.

    Returns: {"created": True, "event_id": str, "title": str}
    """
    return {"created": True, "event_id": "EVT-001", "title": title, "date": date, "time": time}


@mcp.tool(name="productivity__get_schedule")
def get_schedule(date: str = "today") -> dict[str, Any]:
    """Get schedule for a date.

    Args:
        date: Date to query (YYYY-MM-DD or 'today').

    Returns: {"date": str, "events": [{"time": str, "title": str, "duration": int}]}
    """
    return {
        "date": date,
        "events": [
            {"time": "09:00", "title": "Daily Standup", "duration": 15},
            {"time": "10:00", "title": "Project Review", "duration": 60},
            {"time": "14:00", "title": "Client Call", "duration": 30},
        ],
    }


@mcp.tool(name="productivity__create_note")
def create_note(title: str, content: str, tags: list[str] | None = None) -> dict[str, Any]:
    """Create a note.

    Args:
        title: Note title.
        content: Note content.
        tags: Optional tags for organization.

    Returns: {"created": True, "note_id": str, "title": str}
    """
    return {"created": True, "note_id": "NOTE-001", "title": title, "tags": tags or []}


@mcp.tool(name="productivity__search_notes")
def search_notes(query: str) -> dict[str, Any]:
    """Search notes.

    Args:
        query: Search query.

    Returns: {"notes": [{"id": str, "title": str, "preview": str}]}
    """
    return {
        "notes": [
            {"id": "NOTE-001", "title": f"Notes on {query}", "preview": "Key points discussed..."},
            {"id": "NOTE-002", "title": f"{query} ideas", "preview": "Brainstorming session..."},
        ]
    }


@mcp.tool(name="productivity__set_reminder")
def set_reminder(text: str, time: str, repeat: str = "none") -> dict[str, Any]:
    """Set a reminder.

    Args:
        text: Reminder text.
        time: Reminder time (HH:MM or datetime).
        repeat: Repeat frequency (none, daily, weekly).

    Returns: {"set": True, "reminder_id": str, "text": str}
    """
    return {"set": True, "reminder_id": "REM-001", "text": text, "time": time}


@mcp.tool(name="productivity__start_timer")
def start_timer(minutes: int, label: str = "") -> dict[str, Any]:
    """Start a countdown timer (Pomodoro, etc).

    Args:
        minutes: Timer duration in minutes.
        label: Optional label.

    Returns: {"started": True, "minutes": int, "label": str}
    """
    return {"started": True, "minutes": minutes, "label": label}


# === Social ===


@mcp.tool(name="social__post_status")
def post_status(text: str, platform: str = "twitter") -> dict[str, Any]:
    """Post a status update.

    Args:
        text: Status text content.
        platform: Social platform (twitter, facebook, linkedin).

    Returns: {"posted": True, "platform": str, "post_id": str}
    """
    return {"posted": True, "platform": platform, "post_id": "POST-2024-001"}


@mcp.tool(name="social__send_message")
def send_message(to: str, message: str) -> dict[str, Any]:
    """Send a direct message.

    Args:
        to: Recipient username.
        message: Message content.

    Returns: {"sent": True, "to": str, "message_id": str}
    """
    return {"sent": True, "to": to, "message_id": "MSG-2024-001"}


@mcp.tool(name="social__get_notifications")
def get_notifications(platform: str = "all") -> dict[str, Any]:
    """Get notifications.

    Args:
        platform: Platform filter (twitter, facebook, all).

    Returns: {"notifications": [{"type": str, "message": str, "time": str}]}
    """
    return {
        "notifications": [
            {"type": "like", "message": "John liked your post", "time": "5 min ago"},
            {"type": "comment", "message": "Sara commented on your photo", "time": "1 hour ago"},
            {"type": "follow", "message": "New follower: @techguy", "time": "2 hours ago"},
        ]
    }


@mcp.tool(name="social__get_feed")
def get_feed(platform: str = "twitter", count: int = 10) -> dict[str, Any]:
    """Get social media feed.

    Args:
        platform: Social platform.
        count: Number of posts to retrieve.

    Returns: {"posts": [{"author": str, "content": str, "likes": int}]}
    """
    return {
        "posts": [
            {"author": "@techie", "content": "Just shipped a new feature!", "likes": 42},
            {"author": "@designer", "content": "New UI mockups ready", "likes": 28},
            {"author": "@coder", "content": "Debugging at midnight...", "likes": 156},
        ]
    }


@mcp.tool(name="social__follow_user")
def follow_user(username: str, platform: str) -> dict[str, Any]:
    """Follow a user.

    Args:
        username: User to follow.
        platform: Social platform.

    Returns: {"followed": True, "username": str, "platform": str}
    """
    return {"followed": True, "username": username, "platform": platform}


@mcp.tool(name="social__share_link")
def share_link(url: str, comment: str = "", platform: str = "twitter") -> dict[str, Any]:
    """Share a link.

    Args:
        url: URL to share.
        comment: Optional comment.
        platform: Social platform.

    Returns: {"shared": True, "url": str, "post_id": str}
    """
    return {"shared": True, "url": url, "post_id": "POST-2024-002", "platform": platform}


# === Utilities ===


@mcp.tool(name="utilities__translate")
def translate(text: str, to_lang: str, from_lang: str = "auto") -> dict[str, Any]:
    """Translate text.

    Args:
        text: Text to translate.
        to_lang: Target language code (en, ja, es, fr, de, zh).
        from_lang: Source language (auto for detection).

    Returns: {"original": str, "translated": str, "from": str, "to": str}
    """
    return {"original": text, "translated": f"[{to_lang}] {text}", "from": from_lang, "to": to_lang}


@mcp.tool(name="utilities__get_time")
def get_time(timezone: str = "local") -> dict[str, Any]:
    """Get current time.

    Args:
        timezone: Timezone (local, UTC, America/New_York, Asia/Tokyo, etc).

    Returns: {"timezone": str, "time": str, "date": str}
    """
    return {"timezone": timezone, "time": "14:30:00", "date": "2024-01-15"}


@mcp.tool(name="utilities__convert_units")
def convert_units(value: float, from_unit: str, to_unit: str) -> dict[str, Any]:
    """Convert between units.

    Args:
        value: Numeric value.
        from_unit: Source unit.
        to_unit: Target unit.

    Returns: {"value": float, "from": str, "to": str, "result": float}
    """
    conversions = {
        ("km", "miles"): 0.621371,
        ("miles", "km"): 1.60934,
        ("kg", "lbs"): 2.20462,
        ("lbs", "kg"): 0.453592,
        ("c", "f"): lambda x: x * 9 / 5 + 32,
        ("f", "c"): lambda x: (x - 32) * 5 / 9,
    }
    key = (from_unit.lower(), to_unit.lower())
    conv = conversions.get(key, 1.0)
    result: float = conv(value) if callable(conv) else value * (conv if isinstance(conv, float) else 1.0)
    return {"value": value, "from": from_unit, "to": to_unit, "result": round(result, 2)}


@mcp.tool(name="utilities__calculate")
def calculate(expression: str) -> dict[str, Any]:
    """Evaluate a math expression.

    Args:
        expression: Math expression (e.g., "2 + 3 * 4").

    Returns: {"expression": str, "result": float}
    """
    try:
        allowed = set("0123456789+-*/.() ")
        if all(c in allowed for c in expression):
            result = eval(expression)
            return {"expression": expression, "result": result}
        return {"expression": expression, "error": "Invalid expression"}
    except Exception as e:
        return {"expression": expression, "error": str(e)}


@mcp.tool(name="utilities__get_directions")
def get_directions(origin: str, destination: str, mode: str = "driving") -> dict[str, Any]:
    """Get directions between locations.

    Args:
        origin: Starting location.
        destination: End location.
        mode: Travel mode (driving, walking, transit, cycling).

    Returns: {"origin": str, "destination": str, "mode": str, "duration": str, "distance": str}
    """
    return {"origin": origin, "destination": destination, "mode": mode, "duration": "25 min", "distance": "12.5 km"}


@mcp.tool(name="utilities__check_traffic")
def check_traffic(route: str) -> dict[str, Any]:
    """Check traffic conditions.

    Args:
        route: Route name or origin-destination.

    Returns: {"route": str, "condition": str, "delay": str}
    """
    return {"route": route, "condition": "Moderate", "delay": "10 min"}


@mcp.tool(name="utilities__find_nearby")
def find_nearby(location: str, category: str) -> dict[str, Any]:
    """Find nearby places.

    Args:
        location: Current location.
        category: Place category (restaurant, gas_station, pharmacy, atm).

    Returns: {"places": [{"name": str, "distance": str, "rating": float}]}
    """
    return {
        "places": [
            {"name": f"{category.title()} One", "distance": "0.3 km", "rating": 4.5},
            {"name": f"{category.title()} Two", "distance": "0.8 km", "rating": 4.2},
            {"name": f"{category.title()} Three", "distance": "1.2 km", "rating": 4.7},
        ]
    }


@mcp.tool(name="utilities__set_alarm")
def set_alarm(time: str, label: str = "", repeat: list[str] | None = None) -> dict[str, Any]:
    """Set an alarm.

    Args:
        time: Alarm time (HH:MM).
        label: Optional label.
        repeat: Days to repeat (mon, tue, wed, thu, fri, sat, sun).

    Returns: {"set": True, "time": str, "label": str}
    """
    return {"set": True, "time": time, "label": label, "repeat": repeat or []}


if __name__ == "__main__":
    mcp.run(transport="stdio")
