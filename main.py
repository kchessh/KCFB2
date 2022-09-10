year = 2022
weeks = [num for num in range(1, 15)]

from flask import Flask, render_template
import requests
import pandas
import time
import datetime
from collections import OrderedDict
import os, os.path

app = Flask(__name__)

week_choices = {number:str(number) for number in range(1, 16)}

"get_data should be set to true to request data from the CFB API"
get_data = False
""
get_upcoming_games = False

"""
This function is used to determine which week number it is in the season. It will look through the cutoffs (dates) and
compare it to the datetime's current date. It's used to set the default week number from the dropdown for the standings
"""
def determine_week_number():
	var = datetime.datetime.now()
	day = var.day
	month = var.month
	# month = 12

	cutoffs = [[9, 11], [9, 18], [9, 25], [10, 2], [10, 9], [10, 16], [10, 23], [10, 30], [11, 6], [11, 13],
			   [11, 20], [11, 27], [12, 4]]
	list = []
	second_list = []

	for item in cutoffs:
		if month >= item[0]:
			list.append(item)

	for item in list:
		if day >= item[1] or month > item[0]:
			second_list.append(item)

	if len(second_list) == 0:
		week = 1
	else:
		week = len(second_list) + 1
		if week > 14:
			week = 14
	return week

"""
This function will read the people and their respective teams from any given league (saved as a csv) and will return a
dictionary with the person and their total score. This can be used for any given week and only needs to have a
dictionary passed in that has the win total (or points) for every respective school. That dictionary is then read and
is used to determine the total for every person in the league
"""

def determine_scores(points_dict, league_number):
	data = pandas.read_csv(f"Leagues/League{league_number}.csv", encoding='latin-1')
	player_teams = data.to_dict()
	score_dict = {}
	for person in player_teams:
		this_week_score = 0
		for i in range(0, 4):
			team = player_teams[person][i]
			try:
				this_week_score += points_dict[team]
			except KeyError:
				pass
		score_dict[person] = this_week_score
	del score_dict['Unnamed: 0']

	return score_dict

"""
This function requests the college football API to get the game data. It will take any given year (int), week (int), and
team (str)
"""

def get_game_data(year, week, team):
	url = f"http://api.collegefootballdata.com/games?year={year}&week={week}&seasonType=regular&team={team}"

	headers = {
		'Authorization': 'Bearer YuVJiwtjTbmZ+XUvpjipRfpdytZRSr7o29yj5saaXfntEvvVekIkOCcC+nYhPTAH',
	}

	response = requests.get(url, headers=headers)
	data = response.json()
	return data

"""
This function will delete the initial key that Panda makes with the row numbers (Unnamed). It also simplifies it so
that the key (person) will only have a list as the value rather than a list of dictionaries
"""

def convert_dict_to_simple_dict(dict):
	if dict["Unnamed: 0"]:
		del dict["Unnamed: 0"]
	dict_final = {}
	for item in dict:
		list = []
		for i in range(0, 4):
			try:
				team = dict[item][i]
				list.append(team)
			except KeyError:
				break
		dict_final[item] = list
	return dict_final

"""
This loop replaces all teams that have an '&' in their name to '%26' because the API won't find it if an '&' is passed
in. Teams_dict is then made to pass into the save_to_spreadsheet function. A dictionary is made so it can be saved to a
csv with a list of 0s and 1s (1s representing a win, 0s representing a loss or no game played)
"""

new_teams = []
with open("Teams.txt", encoding='ISO-8859-1') as file:
	text = file.read()
	teams = text.split(",")
	for team in teams:
		new_team = team.replace("&", "%26")
		new_teams.append(new_team)

teams_dict = {team: [] for team in teams}

def upcoming_games_master():
	test = True
	games = {}
	weekDays = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
	if test:
		week = 2
		day_of_week = 1
	else:
		var = datetime.datetime.now()
		day_of_week = datetime.date.weekday(var)
		week = determine_week_number() + 1

	if day_of_week == 1:
		for team in teams_dict:
			game = get_game_data(year, week, team.replace("&", "%26"))
			i = 0

			try:
				if game[i]["home_team"] == team:
					start_date = game[i]["start_date"].split("T")[0].split("-")
					start_day_as_input = [int(item) for item in start_date]
					date = datetime.date(start_day_as_input[0], start_day_as_input[1], start_day_as_input[2])
					start_day_as_output = datetime.date.weekday(date)
					start_day = weekDays[start_day_as_output]
					games[team] = {"opponent": game[i]["away_team"], "start_day": start_day}
				else:
					home_team = game[i]["home_team"]
					start_date = game[i]["start_date"].split("T")[0].split("-")
					start_day_as_input = [int(item) for item in start_date]
					date = datetime.date(start_day_as_input[0], start_day_as_input[1], start_day_as_input[2])
					start_day_as_output = datetime.date.weekday(date)
					start_day = weekDays[start_day_as_output]
					games[home_team] = {"opponent": team, "start_day": start_day}
			except KeyError:
				pass
			except IndexError:
				pass
			i += 1

		write_data = pandas.DataFrame(games, index=["opponent", "start_day", "sort_points"])
		write_data.to_csv(f"This_weeks_games.csv")

		number_of_leagues = len([name for name in os.listdir('Leagues')])
		league = 1

		while league <= number_of_leagues:
			data = pandas.read_csv(f"Leagues/League{league}.csv", encoding='latin-1')
			league_games = games
			players_teams_initial = data.to_dict()
			players_teams = convert_dict_to_simple_dict(players_teams_initial)
			for team in league_games:
				# print(f"opponent: {league_games[team]['opponent']}")
				sort_points = 0
				for player in players_teams:
					if team in players_teams[player]:
						sort_points += 1
					if league_games[team]["opponent"] in players_teams[player]:
						sort_points += 1
					if sort_points == 2:
						break
				league_games[team]["sort_points"] = sort_points

			league_games = dict(sorted(league_games.items(), key=lambda kv: kv[1]["sort_points"], reverse=True))
			write_data = pandas.DataFrame(league_games, index=["opponent", "start_day", "sort_points"])
			write_data.to_csv(f"This_Weeks_Games/League{league}.csv")
			league += 1

if get_upcoming_games:
	upcoming_games_master()
data = pandas.read_csv("This_weeks_games.csv", encoding='latin-1')
team_games = data.to_dict()
final_team_games = convert_dict_to_simple_dict(team_games)

"""
This function saves a csv with a dictionary where the key is the team and the value is a list of 0s and 1s to represent
that team's score. It's done this way so that the user can select what week they want to see the scores for. This csv
will be used in the future to allow every league to use a master spreadsheet where the team's wins will be summed up
This function also saves the previous results for every team to a txt file. Each team has their own txt file
"""

def save_data(league_number):
	data = pandas.read_csv(f"Leagues/League{league_number}.csv", encoding='latin-1')
	initial_dict = data.to_dict()
	player_teams = convert_dict_to_simple_dict(initial_dict)
	week = 1
	for team in new_teams:
		time.sleep(0.2)
		week_data = get_game_data(year, week, team)
		i = 0
		score = 0
		while i < len(week_data):
			game = week_data[i]

			home_team = game["home_team"]
			home_score = game["home_points"]
			away_team = game["away_team"]
			away_score = game["away_points"]

			if home_score > away_score:
				winner = home_team
				loser = away_team
			else:
				winner = away_team
				loser = home_team

			if winner == team.replace("%26", "&"):
				score += 1
				try:
					with open(f"Team_Results/{team}.txt", 'r', encoding='ISO-8859-1') as file:
						text = file.read()
						results = text.split(",")
				except FileNotFoundError:
					results = []
				with open(f"Team_Results/{team}.txt", 'a+', encoding='ISO-8859-1') as file:
					if len(results) == 0:
						file.write(f"W {loser.replace('%26', '&')},")
					else:
						most_recent_result = results[-2]
						if most_recent_result != f"W {loser.replace('%26', '&')}":
							file.write(f"W {loser.replace('%26', '&')},")
			else:
				try:
					with open(f"Team_Results/{team}.txt", 'r', encoding='ISO-8859-1') as file:
						text = file.read()
						results = text.split(",")
				except FileNotFoundError:
					results = []
				with open(f"Team_Results/{team}.txt", 'a+', encoding='ISO-8859-1') as file:
					if len(results) == 0:
						file.write(f"L {winner.replace('%26', '&')},")
					else:
						most_recent_result = results[-2]
						if most_recent_result != f"L {winner.replace('%26', '&')}":
							file.write(f"L {winner.replace('%26', '&')},")

			i += 1
		teams_dict[team.replace("%26", "&")].append(score)


	write_data = pandas.DataFrame(teams_dict)
	write_data.to_csv(f"Team_points.csv")

if get_data:
	save_data(league_number=1)

"""
This route will be the main link to see a person's dashboard. It will automatically show the standings for the current
week. It will have a link to display the weeks for someone to choose so they can see the standings from any given week
"""

@app.route("/Dashboard/league=<league_number>")
def display(league_number):
	data = pandas.read_csv("Team_points.csv", encoding='latin-1')

	with open("Teams.txt", encoding='ISO-8859-1') as file:
		text = file.read()
		teams = text.split(",")

	"Determine current week and previous week to calculate standings and previous standings"
	week = determine_week_number()
	if week == 1:
		previous_week = 1
	else:
		previous_week = week - 1

	"""
	Converts csv data to dictionary and it loops through every team (both for the current week and the new week) to get
	everyone's total. It loops through every team and determines their score on the given week and saves it to a
	dictionary (current_week_points_dict and previous_week_points_dict). It will also get data for team standings here
	by generating a dictionary (team_score_dict) that has the point totals for every team that week
	"""

	points_dict = data.to_dict()
	current_week_points_dict = {}
	previous_week_points_dict = {}
	team_score_dict = {}

	for team in teams:
		i = 0
		points = 0
		while i < week:
			points += points_dict[team][i]
			i += 1

		i = 0
		previous_points = 0
		while i < previous_week:
			previous_points += points_dict[team][i]
			i += 1

		current_week_points_dict[team] = points
		previous_week_points_dict[team] = previous_points
		team_score_dict[team] = points

	"""
	The dictionaries generated previously are sorted by score and the places are determined for both the current week
	and the previous week. Everything is then returned to be rendered by the html doc. Point totals are only generated
	for the current weak for the teams but not the people. Then a new dictionary is made that has multiple dictionaries
	for each team (rank, points, last result, player, and conference)
	"""
	current_week_score_dict = dict(sorted(determine_scores(points_dict=current_week_points_dict, league_number=league_number).items(), key=lambda kv: kv[1], reverse=True))
	previous_week_score_dict = dict(sorted(determine_scores(points_dict=previous_week_points_dict, league_number=league_number).items(), key=lambda kv: kv[1], reverse=True))
	team_score_dict_sorted = dict(sorted(team_score_dict.items(), key=lambda kv: kv[1], reverse=True))
	team_data_dict = {team: {"points": ""} for team in team_score_dict_sorted}

	counter = 1
	for team in team_data_dict:
		team_data_dict[team]["rank"] = counter
		counter += 1

	for team, points in team_score_dict_sorted.items():
		team_data_dict[team]["points"] = points

	places = {}
	counter = 1
	for key, value in current_week_score_dict.items():
		places[key] = counter
		counter += 1

	previous_places = {}
	counter = 1
	for key, value in previous_week_score_dict.items():
		previous_places[key] = counter
		counter += 1

	for team in teams:
		team = team.replace("&", "%26")
		with open(f"Team_Results/{team}.txt", 'r', encoding='ISO-8859-1') as file:
			text = file.read()
			games_list = text.split(',')
			previous_game = games_list[-2]
			team_data_dict[team.replace("%26", "&")]["last_result"] = previous_game

	data = pandas.read_csv(f"Leagues/League{league_number}.csv", encoding='latin-1')
	player_teams_initial = data.to_dict()
	player_teams_final = convert_dict_to_simple_dict(player_teams_initial)

	data = pandas.read_csv(f"This_Weeks_Games/League{league_number}.csv", encoding='latin-1')
	team_games = data.to_dict()
	upcoming_team_games = convert_dict_to_simple_dict(team_games)

	"""
	Variables used: week_num is the week number to be used by the html to calculate the standings.
	display_num is to be used to display the week that was generated by default as the most recent week
	score_dict is the dictionary passed to display the current scores.
	places is the dictionary passed to display the current standings of people in the league.
	previous_score_dict is used to generate the previous week's scores of people in the league.
	previous_places is used to generate the previous week's standings of people in the league.
	team_data_dict is used to pass: a team's score, a team's last result, and what conference that team is in.
	player_teams_final passes in what player owns the team (passes a blank result if unowned).
	"""
	return render_template("Dashboard.html", week_num=week, display_num=week, score_dict=current_week_score_dict, places=places,
	previous_score_dict=previous_week_score_dict, previous_places=previous_places, team_data_dict=team_data_dict,
	player_teams_final=player_teams_final, upcoming_team_games=upcoming_team_games, league_number=league_number)

"""
This route shows the dashboard from any given week that the person wants to see. It's the exact same thing as the main
dashboard link except for that it receives the number of the link the person clicked on and uses that as an integer
input to get different standings
"""

@app.route("/Dashboard/league=<league_number>&week=<number_from_website>")
def get_standings(league_number, number_from_website):
	team_data = pandas.read_csv("Team_points.csv", encoding='latin-1')

	with open("Teams.txt", encoding='ISO-8859-1') as file:
		text = file.read()
		teams = text.split(",")

	"Determine current week and previous week to calculate standings and previous standings"
	week = determine_week_number()
	week_number = int(number_from_website)
	if week_number == 1:
		previous_week = 1
	else:
		previous_week = week_number - 1

	"""
	Converts csv data to dictionary and loops through every team (both for the current week and the new week) to get
	everyone's total. It loops through every team and determines their score on the given week and saves it to a
	dictionary (current_week_points_dict and previous_week_points_dict). It will also get data for team standings here
	by generating a dictionary (team_score_dict) that has the point totals for every team that week
	"""
	points_dict = team_data.to_dict()
	current_week_points_dict = {}
	previous_week_points_dict = {}
	team_score_dict = {}

	for team in teams:
		i = 0
		points = 0
		while i < week_number:
			points += points_dict[team][i]
			i += 1

		i = 0
		previous_points = 0
		while i < previous_week:
			previous_points += points_dict[team][i]
			i += 1

		current_week_points_dict[team] = points
		previous_week_points_dict[team] = previous_points
		team_score_dict[team] = points

	"""
	The dictionaries generated previously are sorted by score and the places are determined for both the current week
	and the previous week. Everything is then returned to be rendered by the html doc. Point totals are only generated
	for the current weak for the teams but not the people. Then a new dictionary is made that has multiple dictionaries
	for each team (rank, points, last result, player, and conference)
	"""
	current_week_score_dict = dict(sorted(determine_scores(points_dict=current_week_points_dict, league_number=league_number).items(), key=lambda kv:kv[1], reverse=True))
	previous_week_score_dict = dict(sorted(determine_scores(points_dict=previous_week_points_dict, league_number=league_number).items(), key=lambda kv: kv[1], reverse=True))
	team_score_dict_sorted = dict(sorted(team_score_dict.items(), key=lambda kv: kv[1], reverse=True))
	team_data_dict = {team: {"points": ""} for team in team_score_dict_sorted}

	counter = 1
	for team in team_data_dict:
		team_data_dict[team]["rank"] = counter
		counter += 1

	for team, points in team_score_dict_sorted.items():
		team_data_dict[team]["points"] = points

	places = {}
	counter = 1
	for key, value in current_week_score_dict.items():
		places[key] = counter
		counter += 1

	previous_places = {}
	counter = 1
	for key, value in previous_week_score_dict.items():
		previous_places[key] = counter
		counter += 1

	for team in teams:
		team = team.replace("&", "%26")
		with open(f"Team_Results/{team}.txt", 'r', encoding='ISO-8859-1') as file:
			text = file.read()
			games_list = text.split(',')
			previous_game = games_list[-2]
			team_data_dict[team.replace("%26", "&")]["last_result"] = previous_game

	data = pandas.read_csv(f"Leagues/League{league_number}.csv", encoding='latin-1')
	player_teams_initial = data.to_dict()
	del player_teams_initial["Unnamed: 0"]
	player_teams_final = {}
	for person in player_teams_initial:
		list = []
		for i in range(0, 4):
			team = player_teams_initial[person][i]
			list.append(team)
		player_teams_final[person] = list

	data = pandas.read_csv(f"This_Weeks_Games/League{league_number}.csv", encoding='latin-1')
	team_games = data.to_dict()
	upcoming_team_games = convert_dict_to_simple_dict(team_games)

	"""
	Variables used: week_num is the week number to be used by the html to calculate the standings.
	display_num is to be used to display the week that was generated by default as the most recent week
	score_dict is the dictionary passed to display the current scores.
	places is the dictionary passed to display the current standings of people in the league.
	previous_score_dict is used to generate the previous week's scores of people in the league.
	previous_places is used to generate the previous week's standings of people in the league.
	previous_game_dict is used to show the team's last game (and result).
	team_data_dict is used to pass: a team's score, a team's last result, and what conference that team is in.
	player_teams_final passes in what player owns the team (passes a blank result if unowned).
	"""
	return render_template("Dashboard.html", week_num=week, display_num=week_number, score_dict=current_week_score_dict, places=places,
	previous_score_dict=previous_week_score_dict, previous_places=previous_places, team_data_dict=team_data_dict,
	player_teams_final=player_teams_final, upcoming_team_games=upcoming_team_games, league_number=league_number)

if __name__ == "__main__":
	app.run(debug=True)