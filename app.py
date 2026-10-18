import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import Draw, Geocoder
from shapely.geometry import shape
import pyproj

# Page configuration
st.set_page_config(
    page_title="Lawn Cutting GPS & Pricing App",
    page_icon="🌿",
    layout="wide"
)

# --- SIDEBAR: PRICING & RATE SETTINGS ---
st.sidebar.header("⚙️ Pricing & Rate Settings")

st.sidebar.subheader("Fuel & Labor")
petrol_price = st.sidebar.number_input("Current Petrol Price (R/L)", min_value=0.0, max_value=50.0, value=24.50, step=0.5)
hourly_rate = st.sidebar.number_input("Labor Rate per Hour (R)", min_value=0.0, max_value=1000.0, value=150.0, step=10.0)
transport_fee = st.sidebar.number_input("Transport / Travel Fee (R)", min_value=0.0, max_value=1000.0, value=50.0, step=10.0)

st.sidebar.subheader("Machine Fuel Burn (Litres/Hour)")
blue_burn = st.sidebar.number_input("Big Blue Mower (L/hr)", min_value=0.0, max_value=10.0, value=2.5, step=0.1)
red_burn = st.sidebar.number_input("3-Wheel Red Mower (L/hr)", min_value=0.0, max_value=10.0, value=2.0, step=0.1)
brush_burn = st.sidebar.number_input("Brush Cutters (L/hr each)", min_value=0.0, max_value=10.0, value=1.2, step=0.1)

st.sidebar.subheader("Profit & Markup")
profit_margin = st.sidebar.slider("Labor, Wear & Profit Markup (%)", min_value=0, max_value=50, value=20, step=5)

# --- MAIN APP INTERFACE ---
st.title("🌿 Lawn Cutting GPS & Pricing Calculator")
st.write("Map out properties, measure edges & areas automatically, detect hazard zones, and generate instant client quotations.")

# --- HELPER FUNCTION TO CALCULATE AREA & PERIMETER ---
def get_polygon_metrics(geojson_geometry):
    try:
        poly = shape(geojson_geometry)
        geod = pyproj.Geod(ellps="WGS84")
        # geometry_area_perimeter returns (area in sq meters, perimeter in meters)
        area_sqm, perimeter_m = geod.geometry_area_perimeter(poly)
        return abs(area_sqm), abs(perimeter_m)
    except Exception:
        return 0.0, 0.0

# --- SECTION 1: PROPERTY MAP & YARD DRAWING ---
st.header("1. Property Map & Hazard Detection")
st.write("🔍 Search the address on the top-right, draw the lawn boundary polygon, and drop pins on obstacles/danger zones.")

m = folium.Map(location=[-26.2041, 28.0473], zoom_start=18, tiles="Esri.WorldImagery")

# Add Search Bar (Geocoder)
Geocoder(
    position="topright",
    collapsed=False,
    placeholder="Search address or location...",
    add_marker=True
).add_to(m)

# Add Drawing Tools
draw = Draw(
    export=False,
    position="topleft",
    draw_options={
        "polyline": False,
        "rectangle": True,
        "polygon": True,
        "circle": False,
        "marker": True,  # Used for hazard pins
        "circlemarker": False,
    },
    edit_options={"edit": True}
)
draw.add_to(m)

# Render map
map_output = st_folium(m, width=900, height=450)

# --- EXTRACT DATA & AUTOMATICALLY MEASURE EDGES/AREAS ---
measured_area = 500.0  # Default fallback
measured_edges = 60.0  # Default fallback
hazard_count = 0
hazard_edge_buffer = 0.0

if map_output and "all_drawings" in map_output and map_output["all_drawings"]:
    for drawing in map_output["all_drawings"]:
        geom_type = drawing["geometry"]["type"]
        if geom_type in ["Polygon", "Rectangle"]:
            calc_area, calc_perim = get_polygon_metrics(drawing["geometry"])
            if calc_area > 0:
                measured_area = calc_area
                measured_edges = calc_perim
        elif geom_type == "Point":
            hazard_count += 1
            # Each hazard pin automatically adds 8 meters of edge trimming around the obstacle
            hazard_edge_buffer += 8.0

total_edges = measured_edges + hazard_edge_buffer

# --- SECTION 2: YARD SPECS & EQUIPMENT ---
st.header("2. Yard Specs & Equipment Deployed")

col_1, col_2 = st.columns(2)

with col_1:
    if measured_area != 500.0:
        st.success(f"🎯 Auto-measured: **{measured_area:.1f} m² area** & **{total_edges:.1f} m total edges**")
    else:
        st.info("💡 Draw a polygon on the map above to auto-calculate area and border edges.")

    lawn_size = st.number_input("Lawn Size (square meters)", min_value=10.0, max_value=50000.0, value=float(round(measured_area, 1)), step=10.0)
    edge_length = st.number_input("Edge / Border Length (meters)", min_value=0.0, max_value=5000.0, value=float(round(total_edges, 1)), step=5.0)
    
    condition = st.selectbox(
        "Grass Height & Condition",
        [
            "Standard Summer Maintenance (1.0x)", 
            "Slightly Overgrown / Medium (1.2x)", 
            "Heavy Overgrowth / Thick Grass (1.4x)"
        ]
    )

with col_2:
    st.write("**Active Fleet Selection:**")
    use_blue = st.checkbox("Big Blue Mower (Large open areas)", value=True)
    use_red = st.checkbox("3-Wheel Red Mower (Medium / Corners)", value=True)
    use_brush = st.checkbox("2x Brush Cutters (Edges & Fences)", value=True)
    
    if hazard_count > 0:
        st.warning(f"⚠️ Detected {hazard_count} hazard pin(s) (+{hazard_edge_buffer}m edge trimming added).")

st.markdown("---")

# --- CALCULATION LOGIC ---
blue_rate = 500.0   # m2 per hour
red_rate = 300.0    # m2 per hour
brush_rate = 160.0  # linear meters per hour (combined for 2 brush cutters)

mower_hours = 0.0
if use_blue and use_red:
    mower_hours = lawn_size / ((blue_rate + red_rate) / 2.0)
elif use_blue:
    mower_hours = lawn_size / blue_rate
elif use_red:
    mower_hours = lawn_size / red_rate
else:
    mower_hours = lawn_size / 200.0

edge_hours = (edge_length / brush_rate) if use_brush else 0.0
total_base_hours = mower_hours + edge_hours

multiplier = 1.0
if "Slightly" in condition:
    multiplier = 1.2
elif "Heavy" in condition:
    multiplier = 1.4

hazard_time_buffer = hazard_count * 0.15 
total_work_hours = (total_base_hours * multiplier) + hazard_time_buffer

# Fuel calculation based on active machines
active_machines_count = sum([use_blue, use_red, use_brush])
avg_burn_rate = ((blue_burn if use_blue else 0) + (red_burn if use_red else 0) + ((brush_burn * 2) if use_brush else 0)) / max(1, active_machines_count)
total_fuel_litres = total_work_hours * avg_burn_rate

fuel_expense = total_fuel_litres * petrol_price
labor_cost = total_work_hours * hourly_rate
subtotal = labor_cost + fuel_expense + transport_fee
final_price = subtotal * (1.0 + (profit_margin / 100.0))
price_per_sqm = final_price / max(1.0, lawn_size)

# --- SECTION 3: COST BREAKDOWN & QUOTATION SUMMARY ---
st.header("3. Cost Breakdown & Quotation Summary")

metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
with metric_col1:
    st.metric("Total Yard Size", f"{lawn_size:.1f} m²")
with metric_col2:
    st.metric("Total Edges / Borders", f"{edge_length:.1f} m")
with metric_col3:
    st.metric("Total Fuel Needed", f"{total_fuel_litres:.1f} L")
with metric_col4:
    st.metric("Recommended Quote", f"R {final_price:.2f}", delta=f"R {price_per_sqm:.2f} / m²")

with st.expander("📊 View Itemized Financial Breakdown"):
    st.write(f"- **Property Area:** {lawn_size:.1f} m²")
    st.write(f"- **Edge / Border Length:** {edge_length:.1f} meters (includes {hazard_edge_buffer}m from {hazard_count} hazard markers)")
    st.write(f"- **Grass Condition Modifier:** {condition}")
    st.write(f"- **Estimated Operation Time:** {total_work_hours:.2f} hours")
    st.write(f"- **Fuel Required:** {total_fuel_litres:.1f} Litres (at R {petrol_price}/L = R {fuel_expense:.2f})")
    st.write(f"- **Labor Cost:** R {labor_cost:.2f}")
    st.write(f"- **Transport Fee:** R {transport_fee:.2f}")
    st.write(f"- **Markup ({profit_margin}%):** R {final_price - subtotal:.2f}")

st.markdown("---")

st.subheader("💬 Client WhatsApp Message")
whatsapp_text = (
    f"Hi! Based on our property assessment ({lawn_size:.0f} m² lawn, {edge_length:.0f}m edges), "
    f"our quotation for cutting and clearing is R{final_price:.2f}. Let us know if you'd like to book!"
)
st.text_area("Copy message to send via WhatsApp:", value=whatsapp_text)