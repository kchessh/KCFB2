import pandas
import datetime

def upcoming_games(date):
    day_of_week = datetime.date.weekday(date)
    if day_of_week == 1:
        data = pandas.read_csv("League1.csv")
        write_data = pandas.DataFrame(teams_dict)
        write_data.to_csv(f"This_weeks_games.csv")

date = "2022, 7, 4"
variable = upcoming_games(date)