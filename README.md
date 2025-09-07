PGA Tournament Winner Prediction

Overview:
The motivation behind this project is to determine the chance a designated player has to win a specified tournament.
Currently, the model considers a variety of tournaments spanning 2017-2024.
Eventually, the goal is to create a web app to interface the model so users can utilize the results.

Project Structure:
Data
This folder houses all the files responsible for aggregating, cleaning, and storing the data necessary to train the model.
The data pipeline was created to aggregate the data from three main sources. 
First, PGATour.com provides player statistics at the tournament level.
Second, espn.com provides information on player scores for each tournament. 
Third, the Open-Meteo API provides current and historical weather information for a desired location at a desired time.
The SQLite database houses the raw data, clean data, and computed features. This is important because it allows for robust data quality.

Model Development
This folder contains all of the analysis around feature engineering, feature importance, model development, and model selection. 
Eventually, the final models will be saved and put into production.

Project Planning
This folder holds all the documents used to keep the project organized. Including, the plan for what data to use and the steps from idea conception to deployment. 
Also, some papers were used to develop domain knowledge on popular modeling techniques for golf data.
