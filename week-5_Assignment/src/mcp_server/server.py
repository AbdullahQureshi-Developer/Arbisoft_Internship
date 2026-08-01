from mcp.server.fastmcp import FastMCP
from datetime import datetime
import ast
import operator
import os
import requests

# Create an MCP server
mcp = FastMCP("week5_server")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

REQUEST_TIMEOUT_SECONDS = 10

# --- Resources ---


@mcp.resource("app://docs/student_handbook")
def get_student_handbook() -> str:
    """Return the student handbook documentation."""
    file_path = os.path.join(BASE_DIR, "student_handbook.md")
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    return "Student handbook not found."


@mcp.resource("app://docs/company_policy")
def get_company_policy() -> str:
    """Return the company policy documentation."""
    file_path = os.path.join(BASE_DIR, "company_policy.md")
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    return "Company policy not found."


# --- Tools ---

# Cap exponent magnitude so `calculate` can't be used to hang the process
# with something like "9**9**9**9" (safe_eval already blocks arbitrary code
# execution via the ast whitelist, but unbounded exponentiation is still a
# cheap denial-of-service vector).
MAX_EXPONENT = 1000


def safe_eval(expr):
    """Safely evaluate mathematical expressions."""
    allowed_operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    def _eval(node):
        if isinstance(node, ast.Num):  # <number>
            return node.n
        elif isinstance(node, ast.Constant):  # Python 3.8+ compatibility
            return node.value
        elif isinstance(node, ast.BinOp):  # <left> <operator> <right>
            if isinstance(node.op, ast.Pow):
                exponent = _eval(node.right)
                if abs(exponent) > MAX_EXPONENT:
                    raise ValueError(f"Exponent too large (max {MAX_EXPONENT})")
            return allowed_operators[type(node.op)](_eval(node.left), _eval(node.right))
        elif isinstance(node, ast.UnaryOp):  # <operator> <operand> e.g., -1
            return allowed_operators[type(node.op)](_eval(node.operand))
        else:
            raise TypeError(node)

    return _eval(ast.parse(expr, mode="eval").body)


@mcp.tool()
def calculate(expression: str) -> float:
    """Perform mathematical calculations on an expression (e.g., '250 * 42 + 10')."""
    try:
        return float(safe_eval(expression))
    except Exception as e:
        raise ValueError(f"Failed to evaluate expression: {e}")


@mcp.tool()
def get_weather(city: str) -> str:
    """Return weather information for a given city."""
    try:
        # Step 1: Get latitude & longitude
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1"
        geo_resp = requests.get(geo_url, timeout=REQUEST_TIMEOUT_SECONDS)
        geo_resp.raise_for_status()
        geo = geo_resp.json()

        if "results" not in geo or not geo["results"]:
            return f"City '{city}' not found."

        lat = geo["results"][0]["latitude"]
        lon = geo["results"][0]["longitude"]

        # Step 2: Get weather
        weather_url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}&current=temperature_2m,weather_code"
        )
        weather_resp = requests.get(weather_url, timeout=REQUEST_TIMEOUT_SECONDS)
        weather_resp.raise_for_status()
        weather = weather_resp.json()

        temp = weather["current"]["temperature_2m"]
        return f"Current temperature in {city}: {temp}°C"

    except requests.exceptions.Timeout:
        return f"Weather lookup for '{city}' timed out. Please try again."
    except requests.exceptions.RequestException as e:
        return f"Weather lookup for '{city}' failed: {e}"
    except (KeyError, IndexError):
        return f"Unexpected response format while looking up weather for '{city}'."


@mcp.tool()
def get_current_time() -> str:
    """Return the current date and time."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@mcp.tool()
def convert_temperature(value: float, unit: str) -> float:
    """Convert between Celsius and Fahrenheit.
    Args:
        value: The temperature value.
        unit: The unit of the provided value ('C' or 'F').
    """
    unit = unit.upper()
    if unit == "C":
        return (value * 9 / 5) + 32  # Return F
    elif unit == "F":
        return (value - 32) * 5 / 9  # Return C
    else:
        raise ValueError("Unit must be 'C' or 'F'")


@mcp.tool()
def word_count(text: str) -> int:
    """Count the number of words in a given text."""
    return len(text.split())


if __name__ == "__main__":
    mcp.run()
