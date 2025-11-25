@echo off
echo --- 1. Creating data folder... ---
if not exist "osrm-data" mkdir osrm-data

echo --- 2. Downloading Map (Saudi Arabia & GCC)... ---
echo This is about 250MB. Please wait...
powershell -Command "Invoke-WebRequest https://download.geofabrik.de/asia/gcc-states-latest.osm.pbf -OutFile osrm-data/gcc-states-latest.osm.pbf"

echo --- 3. Extracting Roads (Step 1/3)... ---
docker run -t -v "%cd%/osrm-data:/data" osrm/osrm-backend osrm-extract -p /opt/car.lua /data/gcc-states-latest.osm.pbf

echo --- 4. Partitioning Graph (Step 2/3)... ---
docker run -t -v "%cd%/osrm-data:/data" osrm/osrm-backend osrm-partition /data/gcc-states-latest.osrm

echo --- 5. Customizing Weights (Step 3/3)... ---
docker run -t -v "%cd%/osrm-data:/data" osrm/osrm-backend osrm-customize /data/gcc-states-latest.osrm

echo.
echo ---------------------------------------------------------
echo SETUP COMPLETE!
echo You can now run 'docker-compose up' to start the server.
echo ---------------------------------------------------------
pause