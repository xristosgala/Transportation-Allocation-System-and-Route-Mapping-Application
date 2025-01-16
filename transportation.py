import streamlit as st
import pandas as pd
import openrouteservice
from pulp import LpProblem, LpMinimize, LpVariable, lpSum, value, LpStatus
import folium
from streamlit_folium import st_folium
from openrouteservice import Client
import random
import os

st.title("Transportation Management App")
st.header("1. Upload Your Datasets")

# Upload the three CSV files
supplier_data = st.file_uploader("Choose the supplier Data CSV file", type=["csv"])
client_data = st.file_uploader("Choose the client Data CSV file", type=["csv"])
driver_data = st.file_uploader("Choose the Driver Data CSV file", type=["csv"])
cost_data = st.file_uploader("Choose the Cost Data CSV file", type=["csv"])

if supplier_data is not None and client_data is not None and driver_data is not None and cost_data is not None:
    # Load the datasets
    supplier_df = pd.read_csv(supplier_data)
    client_df = pd.read_csv(client_data)
    drivers_df = pd.read_csv(driver_data)
    cost_df = pd.read_csv(cost_data)

    st.success("All files uploaded successfully!")

    # ORS API Key
    api_key = "5b3ce3597851110001cf6248767bcf5a42874bb4b85b5b5c0bfac601"  # Replace with your actual API key

    # Initialize ORS client
    client = openrouteservice.Client(key=api_key)

    # Prepare coordinates
    supplier_coords = list(zip(supplier_df["Longitude"], supplier_df["Latitude"]))
    client_coords = list(zip(client_df["Longitude"], client_df["Latitude"]))

    # Create a matrix of travel times/distances
    travel_time_matrix = []

    for supplier in supplier_coords:
        row = []
        for client in client_coords:
            try:
                # Fetch travel data from ORS
                route = client.directions(
                    coordinates=[supplier, client],
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
                print(f"Error processing supplier {supplier} and client {client}: {e}")
                row.append(None)  # Append None if an error occurs

        travel_time_matrix.append(row)

    # Save travel time matrix to a DataFrame
    travel_time_df = pd.DataFrame(travel_time_matrix, columns=client_df["Location"], index=supplier_df["Location"])

    # Define the data
    supplier = list(supplier_df['supplier'])  # supplier at supplier1, supplier2
    client = list(client_df['client'])  # client at client1, client2, client3
    driver_hours = list(drivers_df['Working Hours'])  # Maximum hours for each driver
    driver_capacity = list(drivers_df['Max Load (units)'])  # Max capacity for each driver

    # Number of supplier points, client points, and drivers
    num_supplier = len(supplier)
    num_client = len(client)
    num_drivers = len(driver_hours)

    # Create the Linear Programming problem
    prob = LpProblem("supplier-client Allocation with Drivers", LpMinimize)

    # Decision variables
    x = [[[LpVariable(f"x_{i}_{j}_{k}", lowBound=0, cat="Continuous") for k in range(num_drivers)] for j in range(num_client)] for i in range(num_supplier)]
    y = [[[LpVariable(f"y_{i}_{j}_{k}", cat="Binary") for k in range(num_drivers)] for j in range(num_client)] for i in range(num_supplier)]

    # Objective Function: Minimize transportation cost
    prob += lpSum(x[i][j][k] * cost_df.iloc[i, j] for i in range(num_supplier) for j in range(num_client) for k in range(num_drivers))

    # Constraints: Ensure supplier is not exceeded
    for i in range(num_supplier):
        prob += lpSum(x[i][j][k] for j in range(num_client) for k in range(num_drivers)) <= supplier[i], f"supplier_Constraint_{i}"

    # Constraints: Ensure client is fully met
    for j in range(num_client):
        prob += lpSum(x[i][j][k] for i in range(num_supplier) for k in range(num_drivers)) == client[j], f"client_Constraint_{j}"

    # Constraints: Driver working hours
    for k in range(num_drivers):
        prob += lpSum(y[i][j][k] * travel_time_df.iloc[i, j] for i in range(num_supplier) for j in range(num_client)) <= driver_hours[k], f"Driver_Hours_Constraint_{k}"

    # Constraints: Transport-specific quantity limit (x[i][j][k] <= driver_capacity[k])
    for i in range(num_supplier):
        for j in range(num_client):
            for k in range(num_drivers):
                prob += x[i][j][k] <= driver_capacity[k], f"Transport_Limit_Constraint_{i}_{j}_{k}"

    # Constraints: Link x and y (y is 1 if any quantity is delivered by driver k)
    for i in range(num_supplier):
        for j in range(num_client):
            for k in range(num_drivers):
                prob += x[i][j][k] <= y[i][j][k] * client[j], f"Link_x_y_Constraint_{i}_{j}_{k}"

    # Solve the problem
    prob.solve()

    # Display status of the optimization problem
    st.write("Problem Status")

    if LpStatus[prob.status] == "Optimal":
        st.success(f"Status: {LpStatus[prob.status]}")
        st.subheader("2. Problem Results")
        allocation_output = ""
        for i in range(num_supplier):
            for j in range(num_client):
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

    else:
        st.Error("No optimal solution found.")

    # Collecting the routes
    routes = []

    # Assuming x is the decision variable from your optimization problem
    # Example: x[i][j][k] indicates if driver k is delivering from supplier i to client j
    for i in range(num_supplier):
        for j in range(num_client):
            for k in range(num_drivers):
                if value(x[i][j][k]) > 0:
                    routes.append({
                        "driver": k+1,
                        "supplier": i+1,
                        "client": j+1,
                        "quantity": value(x[i][j][k])
                    })

    # Now, you can save the result in a variable (e.g., `saved_routes`)
    saved_routes = routes  # This is your saved result in a variable

    # Function to generate a random color in hex format
    def generate_random_color():
        return "#{:02x}{:02x}{:02x}".format(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))

    # Create a folium map centered at the midpoint of supplier and client coordinates
    map_center = [(supplier_coords[0][1] + client_coords[0][1]) / 2,  # Latitude
                  (supplier_coords[0][0] + client_coords[0][0]) / 2]  # Longitude
    mymap = folium.Map(location=map_center, zoom_start=12,     tiles='CartoDB positron')

    supplier_point_num = 1
    # Add supplier points to the map
    for supplier in supplier_coords:
        folium.Marker(
            location=[supplier[1], supplier[0]],  # Latitude, Longitude for folium
            popup=f"Supplier Point {supplier_point_num}",
            icon=folium.Icon(color='blue', icon='info-sign')
        ).add_to(mymap)
        supplier_point_num += 1

    client_point_num = 1
    # Add client points to the map
    for client in client_coords:
        folium.Marker(
            location=[client[1], client[0]],  # Latitude, Longitude for folium
            popup=f"Client Point {client_point_num}",
            icon=folium.Icon(color='green', icon='info-sign')
        ).add_to(mymap)
        client_point_num += 1

    # Mapping supplier-client pair to a unique color (same color for each driver)
    driver_colors = {}

    # Fetch and draw routes between supplier and client
    for route_info in saved_routes:
        supplier_index = route_info['supplier'] - 1  # Adjust index (0-based)
        client_index = route_info['client'] - 1  # Adjust index (0-based)

        # Create a unique identifier for this driver
        driver_id = route_info['driver']

        # If this driver hasn't been assigned a color, assign one
        if driver_id not in driver_colors:
            driver_colors[driver_id] = generate_random_color()

        # Get route data from ORS
        try:
            route = client.directions(
                coordinates=[(supplier_coords[supplier_index][0], supplier_coords[supplier_index][1]),
                            (client_coords[client_index][0], client_coords[client_index][1])],
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
                popup_content = f"<b>Route from Supplier {route_info['supplier']} to Client {route_info['client']}</b><br>"
                popup_content += "<ul>"
                for other_route in saved_routes:
                    if (other_route['supplier'] == route_info['supplier'] and
                            other_route['client'] == route_info['client']):
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
                print(f"No route found for supplier {route_info['supplier']} and client {route_info['client']}")
        except Exception as e:
            print(f"Error processing route for supplier {route_info['supplier']} and supplier {route_info['client']}: {e}")

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

