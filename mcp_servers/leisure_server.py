"""Leisure domain MCP server: travel, entertainment, smart_home."""

from typing import Any

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Leisure")

# === Travel ===


@mcp.tool(name="travel__search_flights")
def search_flights(origin: str, destination: str, date: str) -> dict[str, Any]:
    """Search for available flights.

    Args:
        origin: Departure airport code (e.g., NRT, LAX).
        destination: Arrival airport code.
        date: Travel date (YYYY-MM-DD).

    Returns: {"flights": [{"airline": str, "departure": str, "arrival": str, "price": int}]}
    """
    return {
        "flights": [
            {"airline": "JAL", "departure": "08:00", "arrival": "12:00", "price": 450},
            {"airline": "ANA", "departure": "10:30", "arrival": "14:30", "price": 420},
            {"airline": "United", "departure": "14:00", "arrival": "18:00", "price": 380},
        ],
        "origin": origin,
        "destination": destination,
        "date": date,
    }


@mcp.tool(name="travel__search_hotels")
def search_hotels(city: str, check_in: str, check_out: str) -> dict[str, Any]:
    """Search for hotels in a city.

    Args:
        city: City name.
        check_in: Check-in date (YYYY-MM-DD).
        check_out: Check-out date (YYYY-MM-DD).

    Returns: {"hotels": [{"name": str, "rating": float, "price_per_night": int}]}
    """
    return {
        "hotels": [
            {"name": "Grand Hotel", "rating": 4.5, "price_per_night": 180},
            {"name": "City Inn", "rating": 4.0, "price_per_night": 95},
            {"name": "Budget Stay", "rating": 3.5, "price_per_night": 55},
        ],
        "city": city,
    }


@mcp.tool(name="travel__get_attractions")
def get_attractions(city: str, category: str = "all") -> dict[str, Any]:
    """Find tourist attractions in a city.

    Args:
        city: City name.
        category: Category filter (museum, park, landmark, restaurant, all).

    Returns: {"attractions": [{"name": str, "category": str, "rating": float}]}
    """
    return {
        "attractions": [
            {"name": f"{city} National Museum", "category": "museum", "rating": 4.7},
            {"name": f"{city} Central Park", "category": "park", "rating": 4.5},
            {"name": f"{city} Tower", "category": "landmark", "rating": 4.8},
        ],
        "city": city,
        "category": category,
    }


@mcp.tool(name="travel__get_weather")
def get_travel_weather(city: str, days: int = 5) -> dict[str, Any]:
    """Get weather forecast for travel planning.

    Args:
        city: City name.
        days: Number of days to forecast.

    Returns: {"city": str, "forecast": [{"day": int, "condition": str, "high": int, "low": int}]}
    """
    conditions = ["Sunny", "Cloudy", "Partly Cloudy", "Rainy", "Clear"]
    forecast = [
        {"day": i + 1, "condition": conditions[i % len(conditions)], "high": 25 - i, "low": 18 - i}
        for i in range(days)
    ]
    return {"city": city, "forecast": forecast}


@mcp.tool(name="travel__convert_currency")
def convert_currency(amount: float, from_curr: str, to_curr: str) -> dict[str, Any]:
    """Convert between currencies.

    Args:
        amount: Amount to convert.
        from_curr: Source currency code (USD, EUR, JPY, GBP).
        to_curr: Target currency code.

    Returns: {"amount": float, "from": str, "to": str, "result": float, "rate": float}
    """
    rates = {"USD": 1.0, "EUR": 0.92, "JPY": 149.5, "GBP": 0.79}
    usd = amount / rates.get(from_curr, 1.0)
    result = usd * rates.get(to_curr, 1.0)
    rate = rates.get(to_curr, 1.0) / rates.get(from_curr, 1.0)
    return {"amount": amount, "from": from_curr, "to": to_curr, "result": round(result, 2), "rate": round(rate, 4)}


@mcp.tool(name="travel__get_visa_info")
def get_visa_info(nationality: str, destination: str) -> dict[str, Any]:
    """Get visa requirements for travel.

    Args:
        nationality: Passport country.
        destination: Destination country.

    Returns: {"nationality": str, "destination": str, "visa_required": bool, "notes": str}
    """
    return {
        "nationality": nationality,
        "destination": destination,
        "visa_required": destination.lower() not in ["japan", "korea", "thailand"],
        "notes": "90-day visa-free entry for tourism",
    }


# === Entertainment ===


@mcp.tool(name="entertainment__search_movies")
def search_movies(query: str, genre: str = "all") -> dict[str, Any]:
    """Search for movies.

    Args:
        query: Search query (title, actor, director).
        genre: Genre filter (action, comedy, drama, horror, all).

    Returns: {"movies": [{"title": str, "year": int, "rating": float}]}
    """
    return {
        "movies": [
            {"title": f"The {query}", "year": 2024, "rating": 8.5},
            {"title": f"{query} Returns", "year": 2023, "rating": 7.8},
            {"title": f"Rise of {query}", "year": 2022, "rating": 7.2},
        ],
        "genre": genre,
    }


@mcp.tool(name="entertainment__get_showtimes")
def get_showtimes(movie: str, location: str) -> dict[str, Any]:
    """Get movie showtimes.

    Args:
        movie: Movie title.
        location: City or zip code.

    Returns: {"movie": str, "theaters": [{"name": str, "times": [str]}]}
    """
    return {
        "movie": movie,
        "theaters": [
            {"name": "Cineplex Downtown", "times": ["14:00", "17:30", "20:00"]},
            {"name": "AMC Mall", "times": ["15:00", "18:00", "21:00"]},
        ],
    }


@mcp.tool(name="entertainment__play_music")
def play_music(query: str, shuffle: bool = False) -> dict[str, Any]:
    """Play music.

    Args:
        query: Song, artist, album, or playlist name.
        shuffle: Whether to shuffle playback.

    Returns: {"playing": str, "artist": str, "album": str}
    """
    return {"playing": query, "artist": "Various Artists", "album": "Top Hits 2024", "shuffle": shuffle}


@mcp.tool(name="entertainment__create_playlist")
def create_playlist(name: str, description: str = "") -> dict[str, Any]:
    """Create a music playlist.

    Args:
        name: Playlist name.
        description: Optional description.

    Returns: {"created": True, "playlist_id": str, "name": str}
    """
    return {"created": True, "playlist_id": "PL-2024-001", "name": name}


@mcp.tool(name="entertainment__get_book_recommendations")
def get_book_recommendations(genre: str, count: int = 5) -> dict[str, Any]:
    """Get book recommendations.

    Args:
        genre: Book genre (fiction, non-fiction, mystery, sci-fi, etc).
        count: Number of recommendations.

    Returns: {"genre": str, "books": [{"title": str, "author": str, "rating": float}]}
    """
    books = [
        {"title": f"The Great {genre.title()}", "author": "J. Smith", "rating": 4.5},
        {"title": f"{genre.title()} Adventures", "author": "A. Jones", "rating": 4.2},
        {"title": f"Beyond {genre.title()}", "author": "M. Brown", "rating": 4.8},
    ]
    return {"genre": genre, "books": books[:count]}


@mcp.tool(name="entertainment__get_podcast_episodes")
def get_podcast_episodes(podcast: str, count: int = 5) -> dict[str, Any]:
    """Get recent podcast episodes.

    Args:
        podcast: Podcast name.
        count: Number of episodes to return.

    Returns: {"podcast": str, "episodes": [{"title": str, "duration": str, "date": str}]}
    """
    episodes = [
        {"title": f"{podcast} Episode {i}", "duration": f"{45 + i} min", "date": f"2024-01-{15 - i}"}
        for i in range(1, count + 1)
    ]
    return {"podcast": podcast, "episodes": episodes}


@mcp.tool(name="entertainment__get_game_info")
def get_game_info(game: str) -> dict[str, Any]:
    """Get video game information.

    Args:
        game: Game title.

    Returns: {"title": str, "platform": [str], "rating": float, "genre": str}
    """
    return {"title": game, "platform": ["PS5", "Xbox", "PC"], "rating": 8.7, "genre": "Action RPG"}


# === Smart Home ===


@mcp.tool(name="smart_home__set_thermostat")
def set_thermostat(temperature: int, mode: str = "auto") -> dict[str, Any]:
    """Set thermostat temperature.

    Args:
        temperature: Target temperature in Celsius.
        mode: Mode (heat, cool, auto).

    Returns: {"set": True, "temperature": int, "mode": str, "current": int}
    """
    return {"set": True, "temperature": temperature, "mode": mode, "current": 22}


@mcp.tool(name="smart_home__control_lights")
def control_lights(room: str, action: str = "toggle", brightness: int = 100) -> dict[str, Any]:
    """Control smart lights.

    Args:
        room: Room name (living_room, bedroom, kitchen, all).
        action: Action (on, off, toggle, dim).
        brightness: Brightness level 0-100 (for dim action).

    Returns: {"room": str, "action": str, "brightness": int, "state": str}
    """
    state = "on" if action in ["on", "toggle"] else "off"
    return {"room": room, "action": action, "brightness": brightness, "state": state}


@mcp.tool(name="smart_home__lock_door")
def lock_door(door: str, action: str = "lock") -> dict[str, Any]:
    """Lock or unlock a smart door lock.

    Args:
        door: Door name (front, back, garage).
        action: Action (lock, unlock).

    Returns: {"door": str, "action": str, "locked": bool}
    """
    return {"door": door, "action": action, "locked": action == "lock"}


@mcp.tool(name="smart_home__check_cameras")
def check_cameras(camera: str = "all") -> dict[str, Any]:
    """Check security camera status.

    Args:
        camera: Camera name or 'all'.

    Returns: {"cameras": [{"name": str, "status": str, "recording": bool}]}
    """
    cameras = [
        {"name": "Front Door", "status": "Online", "recording": True},
        {"name": "Backyard", "status": "Online", "recording": True},
        {"name": "Garage", "status": "Online", "recording": False},
    ]
    if camera != "all":
        cameras = [c for c in cameras if camera.lower() in str(c["name"]).lower()]
    return {"cameras": cameras}


@mcp.tool(name="smart_home__start_vacuum")
def start_vacuum(room: str = "all") -> dict[str, Any]:
    """Start robot vacuum.

    Args:
        room: Room to clean or 'all'.

    Returns: {"started": True, "room": str, "estimated_time": str}
    """
    return {"started": True, "room": room, "estimated_time": "45 minutes"}


@mcp.tool(name="smart_home__set_alarm")
def set_home_alarm(mode: str, time: str = "") -> dict[str, Any]:
    """Set home security alarm.

    Args:
        mode: Alarm mode (arm_away, arm_stay, disarm).
        time: Optional scheduled time (HH:MM).

    Returns: {"mode": str, "scheduled": bool, "time": str}
    """
    return {"mode": mode, "scheduled": bool(time), "time": time}


@mcp.tool(name="smart_home__get_energy_usage")
def get_energy_usage(period: str = "today") -> dict[str, Any]:
    """Get energy usage statistics.

    Args:
        period: Time period (today, week, month).

    Returns: {"period": str, "kwh": float, "cost": float, "comparison": str}
    """
    usage = {"today": 12.5, "week": 85.0, "month": 350.0}
    kwh = usage.get(period, 0)
    return {"period": period, "kwh": kwh, "cost": kwh * 0.12, "comparison": "5% less than last period"}


@mcp.tool(name="smart_home__control_blinds")
def control_blinds(room: str, position: int) -> dict[str, Any]:
    """Control smart blinds.

    Args:
        room: Room name.
        position: Blind position 0-100 (0=closed, 100=open).

    Returns: {"room": str, "position": int, "state": str}
    """
    state = "closed" if position == 0 else "open" if position == 100 else "partial"
    return {"room": room, "position": position, "state": state}


if __name__ == "__main__":
    mcp.run(transport="stdio")
