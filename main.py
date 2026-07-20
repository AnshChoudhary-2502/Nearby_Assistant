import os

from dotenv import load_dotenv
import requests
from langchain_core.tools import tool
from langchain_anthropic import ChatAnthropic
from langgraph.prebuilt import create_react_agent

load_dotenv()

GOOGLE_MAPS_API_KEY = os.environ["GOOGLE_MAPS_API_KEY"]

GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
NEARBY_SEARCH_URL = "https://places.googleapis.com/v1/places:searchNearby"


@tool
def geocode_location(location: str) -> dict:
    """Convert a place name or address (e.g. 'Koramangala, Bangalore') into latitude/longitude coordinates."""
    resp = requests.get(
        GEOCODE_URL,
        params={"address": location, "key": GOOGLE_MAPS_API_KEY},
        timeout=10,
    )
    data = resp.json()
    if data.get("status") != "OK" or not data.get("results"):
        return {"error": f"Could not geocode '{location}': {data.get('status')}"}
    loc = data["results"][0]["geometry"]["location"]
    return {
        "lat": loc["lat"],
        "lng": loc["lng"],
        "formatted_address": data["results"][0]["formatted_address"],
    }


@tool
def find_nearby_places(place_type: str, latitude: float, longitude: float, radius_meters: int = 1500) -> dict:
    """
    Find nearby places of a given type (e.g. "restaurant", "gym", "cafe")
    around a latitude/longitude using the Google Places Nearby Search API.
    """
    body = {
        "includedTypes": [place_type],
        "maxResultCount": 10,
        "locationRestriction": {
            "circle": {
                "center": {"latitude": latitude, "longitude": longitude},
                "radius": radius_meters,
            }
        },
    }
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_MAPS_API_KEY,
        "X-Goog-FieldMask": (
            "places.displayName,places.formattedAddress,places.rating,"
            "places.userRatingCount,places.currentOpeningHours.openNow"
        ),
    }
    resp = requests.post(NEARBY_SEARCH_URL, json=body, headers=headers, timeout=10)
    data = resp.json()
    if "places" not in data:
        return {"error": data}

    results = []
    for place in data["places"]:
        results.append(
            {
                "name": place.get("displayName", {}).get("text"),
                "address": place.get("formattedAddress"),
                "rating": place.get("rating"),
                "rating_count": place.get("userRatingCount"),
                "open_now": place.get("currentOpeningHours", {}).get("openNow"),
            }
        )
    return {"results": results}


def build_agent():
    llm = ChatAnthropic(model="claude-haiku-4-5")
    tools = [geocode_location, find_nearby_places]
    system_prompt = (
        "You are a helpful assistant that finds nearby places like gyms, "
        "restaurants, and cafes for the user. If the user gives a location name "
        "instead of coordinates, first call geocode_location to resolve it. "
        "Always call find_nearby_places to get real results before answering, "
        "and present the results in a clean, conversational way."
    )
    return create_react_agent(llm, tools, prompt=system_prompt)


def main():
    agent = build_agent()
    print("Nearby Assistant — ask about gyms, restaurants, or other places near you. Ctrl+C to exit.\n")
    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break
        if not user_input:
            continue
        result = agent.invoke({"messages": [("user", user_input)]})
        reply = result["messages"][-1].content
        print(f"Assistant: {reply}\n")


if __name__ == "__main__":
    main()
