import folium
from folium.plugins import Draw
import pyproj
import requests
from shapely.geometry import Polygon
from streamlit_folium import st_folium
import streamlit as st

st.set_page_config(
    page_title="Lawn Cutting GPS & Pricing Calculator",
    page_icon="🌿",
    layout="wide",
)

st.title("🌿 Lawn Cutting Business GPS & Pricing")
st.markdown(
    "Map properties, measure area & perimeters, handle obstacles, and generate"
    " client quotes instantly."
)

# --- SIDEBAR: Pricing & Fleet Variables ---
st.sidebar.header("⚙️ Business & Pricing Settings")

st.sidebar.subheader("Fleet Productivity")
big_blue_rate = st.sidebar.number_input(
    "Big Blue Mower (m²/hr)", value=500.0, step=50.0
)
red_mower_rate = st.sidebar.number_input(
    "3-Wheel Red Mower (m²/hr)", value=300.0, step=50.0
)
brush_cutter_rate = st.sidebar.number_input(
    "Brush Cutters (m/hr for edges)", value=160.0, step=20.0
)

st.sidebar.subheader("Cost Rates")
petrol_price = st.sidebar.number_input(
    "Petrol Price per Litre (R)", value=25.0, step=1.0
)
fuel_consumption = st.sidebar.number_input(
    "Fuel Consumption (L/hr)", value=1.5, step=0.1
)
labor_rate = st.sidebar.number_input(
    "Labor Rate per Hour (R/hr)", value=60.0, step=5.0
)
transport_fee = st.sidebar.number_input(
    "Base Transport Fee (R)", value=150.0, step=10.0
)
profit_margin = st.sidebar.slider(
    "Target Profit Margin (%)", min_value=10, max_value=100, value=30, step=5
)

# --- MAIN INTERFACE: Address Search & Map ---
st.subheader("📍 Map & Property Assessment")
st.write(
    "Type an address or location below to center the map, then draw your lawn"
    " boundary polygon and drop hazard pins."
)

# Mobile-friendly search box
search_address = st.text_input(
    "🔍 Search Address",
    placeholder="e.g., 123 Main Road, Johannesburg or Suburb name",
)

# Default coordinates (Johannesburg area)
center_lat, center_lon = -26.2041, 28.0473
zoom = 13

if search_address:
  try:
    url = f"https://nominatim.openstreetmap.org/search?q={search_address}&format=json"
    headers = {"User-Agent": "LawnCuttingApp/1.0"}
    response = requests.get(url, headers=headers).json()
    if response:
      center_lat = float(response[0]["lat"])
      center_lon = float(response[0]["lon"])
      zoom = 19  # Zoom in close to property level
      st.success(f"📍 Centered on: {response[0]['display_name']}")
    else:
      st.warning(
          "Address not found. Try adding the city or suburb name (e.g., 'Sandton,"
          " Johannesburg')."
      )
  except Exception:
    st.error("Could not reach location search. Please try again.")

# Create Folium Map with Satellite Tile Layer (Esri World Imagery)
m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom)

folium.TileLayer(
    tiles=(
        "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/"
        "MapServer/tile/{z}/{y}/{x}"
    ),
    attr="Esri",
    name="Esri Satellite",
    overlay=False,
    control=True,
).add_to(m)

# Add Draw plugin for polygon boundaries and markers
draw = Draw(
    export=False,
    draw_options={
        "polyline": False,
        "rectangle": True,
        "polygon": True,
        "circle": False,
        "marker": True,
        "circlemarker": False,
    },
    edit_options={"edit": True},
)
draw.add_to(m)

# Render map in Streamlit
map_output = st_folium(m, width=700, height=500)

# --- CALCULATIONS & RESULTS ---
lawn_size = 0.0
edge_length = 0.0
hazard_count = 0

if map_output and "all_drawings" in map_output and map_output["all_drawings"]:
  drawings = map_output["all_drawings"]

  for shape in drawings:
    if shape["geometry"]["type"] in ["Polygon", "Rectangle"]:
      coords = shape["geometry"]["coordinates"][0]
      geod = pyproj.Geod(ellps="WGS84")
      lats = [c[1] for c in coords]
      lons = [c[0] for c in coords]
      area, perimeter = geod.polygon_area_perimeter(lons, lats)
      lawn_size += abs(area)
      edge_length += perimeter

    elif shape["geometry"]["type"] == "Point":
      hazard_count += 1

# Apply Hazard adjustments (8m extra edge per pin, 0.15hr time buffer per pin)
extra_edge_from_hazards = hazard_count * 8.0
total_edge = edge_length + extra_edge_from_hazards

mowing_hours = lawn_size / big_blue_rate if big_blue_rate > 0 else 0
edge_hours = total_edge / brush_cutter_rate if brush_cutter_rate > 0 else 0
hazard_buffer_hours = hazard_count * 0.15

total_work_hours = mowing_hours + edge_hours + hazard_buffer_hours
total_fuel_litres = total_work_hours * fuel_consumption

fuel_cost = total_fuel_litres * petrol_price
labor_cost = total_work_hours * labor_rate
subtotal = fuel_cost + labor_cost + transport_fee
final_price = subtotal * (1 + profit_margin / 100)

# --- DISPLAY QUOTE & METRICS ---
st.markdown("---")
st.subheader("📊 Property Assessment Results")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Lawn Area", f"{lawn_size:.1f} m²")
col2.metric("Border Edges", f"{total_edge:.1f} m")
col3.metric("Hazard Pins", f"{hazard_count}")
col4.metric("Est. Time", f"{total_work_hours:.2f} hrs")

with st.expander("🛠️ View Itemized Financial Breakdown"):
  st.write(f"**Estimated Operation Time:** {total_work_hours:.2f} hours")
  st.write(
      f"**Fuel Required:** {total_fuel_litres:.1f} Litres (at R"
      f" {petrol_price}/L = R {fuel_cost:.2f})"
  )
  st.write(f"**Labor Cost:** R {labor_cost:.2f}")
  st.write(f"**Transport Fee:** R {transport_fee:.2f}")
  st.write(f"**Markup ({profit_margin}%):** R {final_price - subtotal:.2f}")

st.markdown("---")
st.subheader("💬 Client WhatsApp Message")
whatsapp_text = (
    f"Hi! Based on our property assessment ({lawn_size:.0f} m² lawn,"
    f" {total_edge:.0f}m edges), our quotation for cutting and clearing is"
    f" R{final_price:.2f}. Let us know if you'd like to book!"
)
st.text_area("Copy message to send via WhatsApp:", value=whatsapp_text)