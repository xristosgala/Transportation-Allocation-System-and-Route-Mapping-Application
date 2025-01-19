# Optimized Transportation Allocation System and Route Mapping App

## Overview

This system implements a **Transportation Allocation Problem** using **Linear Programming (LP)** to optimize the transportation of goods while minimizing costs. It incorporates multiple constraints such as supply limits, demand satisfaction, driver hours, and capacity limits, all to ensure that the transportation system runs efficiently. The problem is solved using **PuLP** (a Python library for LP problems) and results are visualized using **Streamlit** for an interactive web-based experience. Additionally, the solution includes **route mapping** for visualizing supply-demand connections.

## Features
- **Data Upload:** Users can upload four CSV files containing **supply data**, **demand data**, **driver data**, and **cost data**.
- **Optimization Model:** The system formulates and solves an LP model that minimizes transportation costs while satisfying all constraints (e.g., supply, demand, working hours, and capacity).
- **Route Mapping:** Visualizes the routes from supply points to demand points on a map with real-time driving distances/times, using the **OpenRouteService API**.
- **Driver Allocation:** Displays how each driver is allocated to specific deliveries, respecting the constraints like working hours and maximum load capacity.
- **Duals and Slacks:** Outputs the duals and slacks for each constraint to analyze the optimization.

## Mathematical Formulation (Linear Programming Model)

Let:

$$\S_i \text{ is the supply at supply point } i \text{ for } i = 1, 2, \dots, m$$

$$
D_j \text{ is the demand at demand point } j \text{ for } j = 1, 2, \dots, n
$$

$$
C_{ij} \text{ is the cost of transporting from supply point } i \text{ to demand point } j
$$

$$
x_{ijk} \text{ is the quantity of goods transported from supply point } i \text{ to demand point } j \text{ by driver } k
$$

$$
y_{ijk} \text{ is a binary variable indicating whether driver } k \text{ delivers goods from supply point } i \text{ to demand point } j
$$

$$
T_{ij} \text{ is the travel time (in hours) from supply point } i \text{ to demand point } j
$$

$$
H_k \text{ is the maximum working hours available for driver } k
$$

$$
Q_k \text{ is the maximum load capacity for driver } k
$$


### Decision Variables:
- \( x_{ijk} \): Continuous decision variable representing the quantity delivered by driver \( k \) from supply point \( i \) to demand point \( j \).
- \( y_{ijk} \): Binary decision variable representing whether driver \( k \) is assigned to deliver from supply point \( i \) to demand point \( j \).

### Objective Function:
Minimize the total transportation cost:

$$
\min Z = \sum_{i=1}^{m} \sum_{j=1}^{n} \sum_{k=1}^{p} x_{ijk} \cdot C_{ij}
$$

### Constraints:

1. **Supply Constraints:**
   Ensure that the total amount delivered from each supply point does not exceed the supply:

$$
\sum_{j=1}^{n} \sum_{k=1}^{p} x_{ijk} \leq S_i \quad \forall i
$$

2. **Demand Constraints:**
   Ensure that the total amount delivered to each demand point satisfies the demand:

$$
\sum_{i=1}^{m} \sum_{k=1}^{p} x_{ijk} = D_j \quad \forall j
$$

3. **Driver Working Hours:**
   Ensure that the total time spent by each driver does not exceed their available working hours:

$$
\sum_{i=1}^{m} \sum_{j=1}^{n} y_{ijk} \cdot T_{ij} \leq H_k \quad \forall k
$$

4. **Driver Capacity:**
   Ensure that the total quantity delivered by each driver does not exceed their load capacity:

$$
x_{ijk} \leq Q_k \quad \forall i, j, k
$$

5. **Link between \( x_{ijk} \) and \( y_{ijk} \):**
   Ensure that \( x_{ijk} > 0 \) only if driver \( k \) is assigned to the route from supply point \( i \) to demand point \( j \):

$$
x_{ijk} \leq y_{ijk} \cdot D_j \quad \forall i, j, k
$$

### Solving the Model:
The problem is solved using **PuLP**'s **LpProblem** method, which uses available solvers (e.g., CBC) to find the optimal solution.

### Map Visualization:
The application utilizes **Folium** to plot supply and demand points on a map, with routes between them drawn dynamically based on the optimized allocations. The **OpenRouteService API** is used to fetch travel times and distances between points.

## How to Use:

1. **Upload Your Data:** Upload the CSV files containing your **supply**, **demand**, **driver**, and **cost** data. The system expects data to include location coordinates (for mapping) and relevant values for optimization.
   
2. **View Results:** Once the model is solved, the application displays:
   - The allocation of drivers to supply-demand pairs.
   - The total transportation cost.
   - Dual values and slack values for constraints.
   - An interactive map showing the optimized routes.

3. **Download Map:** You can view the generated map, which visually represents the transportation routes between supply and demand locations.

## Requirements:
- **Python 3.x**
- **Streamlit**
- **Pandas**
- **OpenRouteService**
- **PuLP**
- **Folium**
- **OpenRouteService API Key**

## Example Data Format:

### Supply Data (`supply_data.csv`):
| Location | Latitude  | Longitude | Supply |
|----------|-----------|-----------|--------|
| Supply1  | 34.0522   | -118.2437 | 50     |
| Supply2  | 36.7783   | -119.4179 | 60     |

### Demand Data (`demand_data.csv`):
| Location | Latitude  | Longitude | Demand |
|----------|-----------|-----------|--------|
| Demand1  | 34.0522   | -118.2437 | 40     |
| Demand2  | 36.7783   | -119.4179 | 50     |

### Driver Data (`driver_data.csv`):
| DriverID | Max Load (units) | Working Hours |
|----------|------------------|---------------|
| Driver1  | 10               | 8             |
| Driver2  | 15               | 10            |

### Cost Data (`cost_data.csv`):
| From / To | Demand1 | Demand2 |
|-----------|---------|---------|
| Supply1   | 100     | 150     |
| Supply2   | 120     | 140     |

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments
- **PuLP** for Linear Programming formulation.
- **OpenRouteService** for travel time and distance calculation.
- **Folium** for map visualization.

