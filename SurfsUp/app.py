#################################################
#Import your dependencies
#################################################

from flask import Flask, jsonify, escape

import sqlalchemy
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, func
import datetime as dt
import pandas as pd

#################################################
#Database Setup
#################################################

engine = create_engine("sqlite:///../Resources/hawaii.sqlite")

#Reflect an existing database into a new model
Base = automap_base()

#Reflect the tables
Base.prepare(autoload_with = engine)

#Save references to the tables
Measure = Base.classes.measurement
Station = Base.classes.station

#Start a session and store start and end dates, most active station
session = Session(engine)

most_recent = session.query(Measure.date).order_by(Measure.date.desc()).first()
date_word_list = most_recent[0].split("-")
date_list = [int(x) for x in date_word_list]
end_date = dt.date(date_list[0], date_list[1], date_list[2])

# Calculate the date one year from the last date in data set.
start_date = end_date-dt.timedelta(days = 365)

#Query for the most active station
most_active = session.query(Measure.station, func.count(Measure.station)).\
    group_by(Measure.station).\
    order_by(func.count(Measure.station).desc()).first()


#Close this session
session.close()

#################################################
#Setup Flask
#################################################

app = Flask(__name__)

#################################################
#Flask Routes
#################################################

@app.route("/")
def welcome():
    """Return all available routes"""

    #Provide endpoints for copy/paste, but also include hyperlinks where relevant
    return(f'The available routes are: <br/>'
           f'<a href ="/api/v1.0/precipitation">Precipitation Over Last 12 Months: /api/v1.0/precipitation</a> <br/>'
           f'<a href = "/api/v1.0/stations"> Stations: /api/v1.0/stations </a> <br/>'
           f'<a href = "/api/v1.0/tobs"> Most Recent 12 Months of Temperature Data for Station {most_active[0]}: /api/v1.0/tobs </a> <br/>'
           f'Search by Start Date: {escape("/api/v1.0/<start>")} <br/>'
           f'Search by Date Range: {escape("/api/v1.0/<start>/<end>")} <br/>')

@app.route("/api/v1.0/precipitation")
def precipitation():
    """Return precipitation values for the last 12 months as JSON"""

    # Perform a query to retrieve the data and precipitation scores for the last 12 months
    data = session.query(Measure.date, Measure.prcp).\
    filter(Measure.date >= start_date).\
    filter(Measure.date <= end_date)

    #Contruct the dictionary with the desired keys and values
    dict = {}
    for date, prcp in data:
        dict[date]=prcp
    
    #Close the SQLAlchemy session
    session.close()

    #Return as JSON
    return jsonify(dict)

@app.route("/api/v1.0/stations") 
def stations():
    """"Return the data for the Stations as JSON"""

    #Query the database for the needed data
    data = session.query(Station.station, Station.name, Station.latitude, Station.longitude, \
                         Station.elevation).all()
    
    #Store the query results as a list of dictionaries based on station names
    station_list = []
    for station, name, lat, lon, elev in data:
        name_dict = {}
        station_dict = {}
        name_dict[name] = station_dict
        station_dict["Station"] = station
        station_dict["Latitude"] = lat
        station_dict["Longitude"] = lon
        station_dict["Elevation"] = elev

        #Create a dictionary of the temperature data for each station
        temps = session.query(Measure.date, Measure.prcp, Measure.tobs).filter(Measure.station == station).all()
        temps_df = {}
        for date, prcp, tobs in temps:
            temps_df[date]={"Precipitation":prcp, "Temperature":tobs}
        station_dict["temperature_data"] = temps_df
        station_list.append(name_dict)

    #Close the SQLAlchemy session
    session.close()

    #Return as JSON
    return jsonify(station_list)

@app.route("/api/v1.0/tobs")
def temperatures():
    """Return temperature data from the last 12 months in the most active station as JSON"""

    #Query the database for the necessary data
    temp_data = session.query(Measure.date, Measure.tobs).\
        filter(Measure.date >= start_date).\
        filter(Measure.date <= end_date).\
        filter(Measure.station == most_active[0]).all()
    
    #Put query results into a dictionary to jsonify
    temp_dict = {}
    for date, temp in temp_data:
        temp_dict[date]=temp

    #Close your session
    session.close()

    #Return your results
    return jsonify(temp_dict)

@app.route("/api/v1.0/<start>")
def descriptor(start):
    """Return a JSON list of min temp, max temp, average temp for all dates >= start"""
    
    #Query the database for needed information separately so that we can store date and station data from
    #the observation
    minimum = session.query(func.min(Measure.tobs), Measure.date, Measure.station).\
        filter(Measure.date >= start).one()
    maximum = session.query(func.max(Measure.tobs), Measure.date, Measure.station).\
        filter(Measure.date >= start).one()
    average = session.query(func.avg(Measure.tobs), Measure.date).\
        filter(Measure.date >= start).one()
    
    #Store these results in a dictionary
    descriptor_df = {}
    descriptor_df["Minimum"]={"Value": minimum[0], "date_observed": minimum[1], "observation_station": minimum[2]}
    descriptor_df["Maximum"]={"Value": maximum[0], "date_observed": maximum[1], "observation_station": maximum[2]}
    descriptor_df["Average"]={"Value": average[0], "Since": average[1]}

    #Close the session
    session.close()

    #Return results in JSON
    return jsonify(descriptor_df)

@app.route("/api/v1.0/<start>/<end>")
def description(start, end):
    """Return a JSON list of min temp, max temp, average temp for all dates between start and end, inclusive"""
    
    #Query the database for needed information separately so that we can store date and station data from
    #the observation
    min2 = session.query(func.min(Measure.tobs), Measure.date, Measure.station).\
        filter(Measure.date >= start).\
        filter(Measure.date <= end).one()
    max2 = session.query(func.max(Measure.tobs), Measure.date, Measure.station).\
        filter(Measure.date >= start).\
        filter(Measure.date <= end).one()
    avg2 = session.query(func.avg(Measure.tobs), Measure.date).\
        filter(Measure.date >= start).\
        filter(Measure.date <= end).one()
    
    #Store these results in a dictionary
    description_df = {}
    description_df["Minimum"]={"Value": min2[0], "date_observed": min2[1], "observation_station": min2[2]}
    description_df["Maximum"]={"Value": max2[0], "date_observed": max2[1], "observation_station": max2[2]}
    description_df["Average"]={"Value": avg2[0], "Between": {"Start": start, "End": end}}

    #Close the session
    session.close()

    #Return results in JSON
    return jsonify(description_df)

if __name__ == "__main__":
    app.run(debug = True)