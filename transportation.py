import streamlit as st
import pandas as pd
import openrouteservice
from pulp import LpProblem, LpMinimize, LpVariable, lpSum, value, LpStatus
import folium
from streamlit_folium import st_folium
from openrouteservice import Client
import random
import os

st.title("Optimiized Transportation Allocation System and Route Mapping App")
st.header("1. Upload Your Datasets")

# Upload the three CSV files
supply_data = st.file_uploader("Choose the Supply Data CSV file", type=["csv"])
demand_data = st.file_uploader("Choose the Demand Data CSV file", type=["csv"])
driver_data = st.file_uploader("Choose the Driver Data CSV file", type=["csv"])
cost_data = st.file_uploader("Choose the Cost Data CSV file", type=["csv"])

if supply_data is not None and demand_data is not None and driver_data is not None and cost_data is not None:
    # Load the datasets
    supply_df = pd.read_csv(supply_data)
    demand_df = pd.read_csv(demand_data)
    drivers_df = pd.read_csv(driver_data)
    cost_df = pd.read_csv(cost_data)

    st.success("All files uploaded successfully!")

    #api_key = {
     #   "authorization": st.secrets["api_key"],
      #  "content_type": "application/json"}

    # Access the API key securely from Streamlit secrets
    api_key = st.secrets["api_key"]
    
    # Initialize ORS client
    client = openrouteservice.Client(key=api_key)

    # Prepare coordinates
    supply_coords = list(zip(supply_df["Longitude"], supply_df["Latitude"]))
    demand_coords = list(zip(demand_df["Longitude"], demand_df["Latitude"]))

    # Create a matrix of travel times/distances
    travel_time_matrix = []

    for supply in supply_coords:
        row = []
        for demand in demand_coords:
            try:
                # Fetch travel data from ORS
                route = client.directions(
                    coordinates=[supply, demand],
                    profile='driving-car',  # Mode of transportation: car
                    format='geojson'
                )

                # Extract travel time in minutes from the 'features' structure
                if 'features' in route and len(route['features']) > 0:
                    feature = route['features'][0]  # Access the first feature
                    if 'properties' in feature and 'summary' in feature['properties']:
                        duration_seconds = feature['properties']['summary']['duration']
                        travel_time = duration_seconds / 3600  # Convert to hours
                    else:
                        travel_time = None  # No summary found
                else:
                    travel_time = None  # No features found

                # Handle cases where travel time is effectively zero
                if travel_time == 0:
                    travel_time = None  # Adjust based on your application's needs

                row.append(travel_time)
            except Exception as e:
                print(f"Error processing supply {supply} and demand {demand}: {e}")
                row.append(None)  # Append None if an error occurs

        travel_time_matrix.append(row)

    # Save travel time matrix to a DataFrame
    travel_time_df = pd.DataFrame(travel_time_matrix, columns=demand_df["Location"], index=supply_df["Location"])

    # Define the data
    supply = list(supply_df['Supply'])  # Supply at Supply1, Supply2
    demand = list(demand_df['Demand'])  # Demand at Demand1, Demand2, Demand3
    driver_hours = list(drivers_df['Working Hours'])  # Maximum hours for each driver
    driver_capacity = list(drivers_df['Max Load (units)'])  # Max capacity for each driver

    # Number of supply points, demand points, and drivers
    num_supply = len(supply)
    num_demand = len(demand)
    num_drivers = len(driver_hours)

    # Create the Linear Programming problem
    prob = LpProblem("Supply-Demand Allocation with Drivers", LpMinimize)

    # Decision variables
    x = [[[LpVariable(f"x_{i}_{j}_{k}", lowBound=0, cat="Continuous") for k in range(num_drivers)] for j in range(num_demand)] for i in range(num_supply)]
    y = [[[LpVariable(f"y_{i}_{j}_{k}", cat="Binary") for k in range(num_drivers)] for j in range(num_demand)] for i in range(num_supply)]

    # Objective Function: Minimize transportation cost
    prob += lpSum(x[i][j][k] * cost_df.iloc[i, j] for i in range(num_supply) for j in range(num_demand) for k in range(num_drivers))

    # Constraints: Ensure supply is not exceeded
    for i in range(num_supply):
        prob += lpSum(x[i][j][k] for j in range(num_demand) for k in range(num_drivers)) <= supply[i], f"Supply_Constraint_{i}"

    # Constraints: Ensure demand is fully met
    for j in range(num_demand):
        prob += lpSum(x[i][j][k] for i in range(num_supply) for k in range(num_drivers)) == demand[j], f"Demand_Constraint_{j}"

    # Constraints: Driver working hours
    for k in range(num_drivers):
        prob += lpSum(y[i][j][k] * travel_time_df.iloc[i, j] for i in range(num_supply) for j in range(num_demand)) <= driver_hours[k], f"Driver_Hours_Constraint_{k}"

    # Constraints: Transport-specific quantity limit (x[i][j][k] <= driver_capacity[k])
    for i in range(num_supply):
        for j in range(num_demand):
            for k in range(num_drivers):
                prob += x[i][j][k] <= driver_capacity[k], f"Transport_Limit_Constraint_{i}_{j}_{k}"

    # Constraints: Link x and y (y is 1 if any quantity is delivered by driver k)
    for i in range(num_supply):
        for j in range(num_demand):
            for k in range(num_drivers):
                prob += x[i][j][k] <= y[i][j][k] * demand[j], f"Link_x_y_Constraint_{i}_{j}_{k}"

    # Solve the problem
    prob.solve()

    # Display status of the optimization problem
    st.write("Problem Status")

    if LpStatus[prob.status] == "Optimal":
        st.success(f"Status: {LpStatus[prob.status]}")
        st.subheader("2. Problem Results")
        allocation_output = ""
        for i in range(num_supply):
            for j in range(num_demand):
                for k in range(num_drivers):
                    if value(x[i][j][k]) > 0:
                        allocation_output += f"Driver {k + 1} delivers {value(x[i][j][k])} units from Supplier {i + 1} to Client {j + 1}\n"
        st.text(allocation_output)  # Display allocation in text format
        st.write(f"Total Cost: {value(prob.objective)}")

        st.subheader("3. Duals and Slacks")

        duals_slacks = ""
        for name, constraint in prob.constraints.items():
            duals_slacks += f"{name}: Dual = {constraint.pi}, Slack = {constraint.slack}\n"
        st.text(duals_slacks)

        # Collecting the routes
        routes = []
    
        # Assuming x is the decision variable from your optimization problem
        # Example: x[i][j][k] indicates if driver k is delivering from supply i to demand j
        for i in range(num_supply):
            for j in range(num_demand):
                for k in range(num_drivers):
                    if value(x[i][j][k]) > 0:
                        routes.append({
                            "driver": k+1,
                            "supply": i+1,
                            "demand": j+1,
                            "quantity": value(x[i][j][k])
                        })
    
        # Now, you can save the result in a variable (e.g., `saved_routes`)
        saved_routes = routes  # This is your saved result in a variable
    
        # Function to generate a random color in hex format
        def generate_random_color():
            return "#{:02x}{:02x}{:02x}".format(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
    
        # Create a folium map centered at the midpoint of supply and demand coordinates
        map_center = [(supply_coords[0][1] + demand_coords[0][1]) / 2,  # Latitude
                      (supply_coords[0][0] + demand_coords[0][0]) / 2]  # Longitude
        mymap = folium.Map(location=map_center, zoom_start=12,     tiles='CartoDB positron')
    
        supply_point_num = 1
        # Add supply points to the map
        for supply in supply_coords:
            folium.Marker(
                location=[supply[1], supply[0]],  # Latitude, Longitude for folium
                popup=f"Supplier {supply_point_num}",
                icon=folium.Icon(color='blue', icon='info-sign')
            ).add_to(mymap)
            supply_point_num += 1
    
        demand_point_num = 1
        # Add demand points to the map
        for demand in demand_coords:
            folium.Marker(
                location=[demand[1], demand[0]],  # Latitude, Longitude for folium
                popup=f"Client {demand_point_num}",
                icon=folium.Icon(color='green', icon='info-sign')
            ).add_to(mymap)
            demand_point_num += 1
    
        # Mapping supply-demand pair to a unique color (same color for each driver)
        driver_colors = {}
    
        # Fetch and draw routes between supply and demand
        for route_info in saved_routes:
            supply_index = route_info['supply'] - 1  # Adjust index (0-based)
            demand_index = route_info['demand'] - 1  # Adjust index (0-based)
    
            # Create a unique identifier for this driver
            driver_id = route_info['driver']
    
            # If this driver hasn't been assigned a color, assign one
            if driver_id not in driver_colors:
                driver_colors[driver_id] = generate_random_color()
    
            # Get route data from ORS
            try:
                route = client.directions(
                    coordinates=[(supply_coords[supply_index][0], supply_coords[supply_index][1]),
                                (demand_coords[demand_index][0], demand_coords[demand_index][1])],
                    profile='driving-car',
                    format='geojson'
                )
    
                # Check if the response contains routes
                if 'features' in route and len(route['features']) > 0:
                    # Extract coordinates of the route
                    route_coords = route['features'][0]['geometry']['coordinates']
    
                    # Convert route coordinates to (lat, lon) for folium
                    route_coords = [(coord[1], coord[0]) for coord in route_coords]  # (Latitude, Longitude)
    
                    # Prepare popup content for all drivers on this route
                    popup_content = f"<b>Route from Supplier {route_info['supply']} to Client {route_info['demand']}</b><br>"
                    popup_content += "<ul>"
                    for other_route in saved_routes:
                        if (other_route['supply'] == route_info['supply'] and
                                other_route['demand'] == route_info['demand']):
                            popup_content += f"<li>Driver {other_route['driver']}: {other_route['quantity']} quantity</li>"
                    popup_content += "</ul>"
    
                    # Use the preassigned color for this driver
                    route_color = driver_colors[driver_id]
    
                    # Add the route to the map
                    folium.PolyLine(
                        locations=route_coords,
                        color=route_color,
                        weight=3,
                        opacity=0.8,
                        popup=folium.Popup(popup_content, max_width=300)
                    ).add_to(mymap)
                else:
                    print(f"No route found for Supplier {route_info['supply']} and Client {route_info['demand']}")
            except Exception as e:
                print(f"Error processing route for Supplier {route_info['supply']} and Client {route_info['demand']}: {e}")
    
        # Save the map to an HTML file
        static_map_path = "static_map.html"
        mymap.save(static_map_path)
    
        # Read and serve the map as static content
        st.subheader("4. Route Map")
    
        # Get the absolute path of the saved HTML file
        html_path = os.path.abspath(static_map_path)
    
        # Open the HTML file and read its content
        with open(html_path, "r") as file:
            html_content = file.read()
    
        # Serve the map as an iframe
        st.components.v1.html(html_content, width=700, height=500)
    else:
            st.error("No optimal solution found. Please, change the data.")
