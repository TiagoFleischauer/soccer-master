import os
import requests
import urllib.parse

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps

import datetime
from datetime import date

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///soccermaster.db")

# Get today's date and tomorrow's date
td = date.today()
tm = datetime.date.today() + datetime.timedelta(days=1)

# Format data string
today = td.strftime("%Y-%m-%d")
tomorrow = tm.strftime("%Y-%m-%d")

def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


# Function that calls all games from the provided API league id
def lookup_games_by_league(league_id):

    # Set all needed info to call API
    url = "https://api-football-v1.p.rapidapi.com/v3/fixtures"

    # Ensures that will be called only the right leagues
    if league_id == "71" or league_id == "253" or league_id == "39":
        querystring = {"from":today,"to":tomorrow,"league":league_id,"season":"2022", "status":"NS"}
    else:
        return False

    headers = {
        'x-rapidapi-host': "api-football-v1.p.rapidapi.com",
        'x-rapidapi-key': "37a4514143mshd83910dfdb06553p16a26fjsn97089317f64e"
        }

    response = requests.request("GET", url, headers=headers, params=querystring)

    r = response.json()

    # Ensures the api call is correct, returning if so
    if "response" in r:
        return r["response"]
    else:
        return None


# Function that gets all the user guesses and updates it
def update_games():

    # Set list that will store all the guesses
    guessed_games = []

    # Get the current not updated guesses from database
    guesses = db.execute("SELECT * FROM guesses WHERE user_id = ? ORDER BY timestamp DESC", session["user_id"])

    for guess in guesses:

        # Get the game info from the database
        game = db.execute("SELECT * FROM fixtures WHERE api_id = ?", guess["fixture_id"])

        # Check if the result of the guess in the database is "NF" ("Not Finished")
        if guess["result"] == "NF":

            # Make api call

            url = "https://api-football-v1.p.rapidapi.com/v3/fixtures"

            headers = {
                'x-rapidapi-host': "api-football-v1.p.rapidapi.com",
                'x-rapidapi-key': "37a4514143mshd83910dfdb06553p16a26fjsn97089317f64e"
                }

            querystring = {"id":guess["fixture_id"]}
            response = requests.request("GET", url, headers=headers, params=querystring)
            r = response.json()

            # Check if the API returned correctly and the game in fact have finished
            if "response" in r:
                if r["response"][0]["fixture"]["status"]["short"] == "FT":

                    # Get the home team's and away team's name
                    home = r["response"][0]["teams"]["home"]["name"]
                    away = r["response"][0]["teams"]["away"]["name"]

                    # Store the guess from the user (Name of home team/Name of away team/"Draw")
                    guessed_result = guess["guess"]

                    # Store the game result
                    if r["response"][0]["teams"]["home"]["winner"]:
                        game_result = home
                    elif r["response"][0]["teams"]["away"]["winner"]:
                        game_result = away
                    else:
                        game_result = "Draw"

                    # Get user info from database
                    row = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])

                    # Check if the user guess is equal to the game result
                    if guess["guess"] == game_result:

                        result = "Correct"

                        # Update the users table, adding 1 to "right_guesses"
                        right_guesses = row[0]["right_guesses"] + 1
                        db.execute("UPDATE users SET right_guesses = ? WHERE id = ?", right_guesses, session["user_id"])
                    else:

                        result = "Incorrect"

                        # Update the users table, adding 1 to "wrong_guesses"
                        wrong_guesses = row[0]["wrong_guesses"] + 1
                        db.execute("UPDATE users SET wrong_guesses = ? WHERE id = ?", wrong_guesses, session["user_id"])

                    # Update the guesses and fixtures tables, setting the results, scores, etc.
                    db.execute("UPDATE guesses SET result = ? WHERE user_id = ? AND fixture_id = ?", result, session["user_id"], guess["fixture_id"])
                    db.execute("UPDATE fixtures SET home_score = ?, away_score = ?, status = ? WHERE api_id = ?", r["response"][0]["goals"]["home"], r["response"][0]["goals"]["away"], r["response"][0]["fixture"]["status"]["long"], r["response"][0]["fixture"]["id"])

        # Get the updated guess from the database
        updated_guess = db.execute("SELECT * FROM guesses WHERE user_id = ? AND fixture_id = ?", session["user_id"], guess["fixture_id"])

        # Get the updated game from the database
        game = db.execute("SELECT * FROM fixtures WHERE api_id = ?", guess["fixture_id"])

        # Store all the required info from the guesses in the game list.
        # This will be used to access not only the game info, but the guess info in the same variable.
        game[0]["guess"] = updated_guess[0]["guess"]
        game[0]["timestamp"] = updated_guess[0]["timestamp"]
        game[0]["result"] = updated_guess[0]["result"]
        game[0]["combined"] = updated_guess[0]["combined"]

        # Append to the guessed games list
        guessed_games += game

    # Returns the list which contains all the games and guesses updated info
    return guessed_games


# Function that updates the user cash
def update_cash():

    # Get the user guesses
    guesses = db.execute("SELECT * FROM guesses WHERE user_id = ?", session["user_id"])

    for guess in guesses:

        # Get the compiled guesses
        # (Compiled guesses is a table which stores all the games that gave or took cash from the user - Games that were finished and already gave "feedback" to the user)
        compiled_guesses = db.execute("SELECT * FROM compiled_guesses")
        # Transform in a list
        list_of_guesses_compiled = [value for elem in compiled_guesses for value in elem.values()]

        # Check if the guess was already compiled
        if guess["id"] not in list_of_guesses_compiled:

            # Check if game is combined
            if guess["combined"] == True:

                # If the game is combined, it's necessary to get all the other fixtures from the group that the game belongs
                combined_guesses = db.execute("SELECT * FROM guesses WHERE user_id = ? AND timestamp = ?", session["user_id"], guess["timestamp"])
                list_of_guesses = [value for elem in combined_guesses for value in elem.values()]

                # Get the number of games in the group that have not finished
                games_not_finished = list_of_guesses.count("NF")

                # Check if all games have finished
                if games_not_finished == 0:

                    # Get the number of wrong guesses
                    wrong_guesses = list_of_guesses.count("Incorrect")

                    # Check if the user got any guess wrong
                    if wrong_guesses == 0:

                        # Set cash to what the user would normally win, multiplied by the number of combined guesses
                        cash = 100 * (len(combined_guesses) * len(combined_guesses))
                    else:
                        # Set cash to what the user would lose if guessed all games wrong, multiplied by the number of combined guesses
                        cash = -30 * (len(combined_guesses) * len(combined_guesses))

                    # Insert all combined guesses from the group to the compiled guesses table
                    for combined_guess in combined_guesses:
                        db.execute("INSERT INTO compiled_guesses (guess_id) VALUES(?)", combined_guess["id"])

                else:
                    # If at least 1 game have not finished, because it's a combined guess, it still can't be compiled
                    cash = 0

            else:
                # If it's not a combined guess, just check if the guess is correct or not and update the cash variable
                if guess["result"] == "Correct":
                    cash = 100
                elif guess["result"] == "Incorrect":
                    cash = -30
                else:
                    # If the game have not finished, set cash to 0
                    cash = 0

            # Get user info
            row = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])
            # Update the user cash and the total received cash
            db.execute("UPDATE users SET cash = ?, received = ? WHERE id = ?", row[0]["cash"] + cash, row[0]["received"] + cash, session["user_id"])

            # Get list of all compiled guesses
            compiled_guesses = db.execute("SELECT * FROM compiled_guesses")
            list_of_guesses_compiled = [value for elem in compiled_guesses for value in elem.values()]

            # Check if the cash variable was "updated" and guess it's not in the compiled guesses list
            if cash != 0 and guess["id"] not in list_of_guesses_compiled:
                # Insert the guess into the compiled guesses table
                db.execute("INSERT INTO compiled_guesses (guess_id) VALUES(?)", guess["id"])


# Function that updates the user level
def update_level():

    # Get the number of right guesses from the user
    user_info = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])
    right_guesses = user_info[0]["right_guesses"]

    # Set the level according to the number of right guesses
    if right_guesses >= 2 and right_guesses < 4:
        level = 2
    elif right_guesses >= 4 and right_guesses < 6:
        level = 3
    elif right_guesses >= 6 and right_guesses < 8:
        level = 4
    else:
        level = right_guesses - 3

    # Check if it's necessary to update the user level
    if right_guesses > 1:
        # If so, updates the users table
        db.execute("UPDATE users SET level = ? WHERE id = ?", level, session["user_id"])


# Function that gets the standings of the provided league
def get_standings(league_id):

    # Make API call
    url = "https://api-football-v1.p.rapidapi.com/v3/standings"

    querystring = {"season":"2021","league":league_id}

    headers = {
        'x-rapidapi-host': "api-football-v1.p.rapidapi.com",
        'x-rapidapi-key': "37a4514143mshd83910dfdb06553p16a26fjsn97089317f64e"
        }

    response = requests.request("GET", url, headers=headers, params=querystring)

    r = response.json()

    # Set dict standings
    standings = {}

    # Check if api returned correctly
    if "response" in r:

        # Check if the league id corresponds to the MLS id.
        # Note: The MLS standings are different from the other leagues. MLS has 2 conferences, dividing all the teams into 2 tables.
        # For that reason, it's necessary to store in the "standings" dict not only the position of a team in the league, as well if it's "W" (West) or "E" (East)
        if league_id == "253":
            for game in r["response"][0]["league"]["standings"][0]:
                # Stores the name of the team as a key, and the value is it's position in the league with the "E" of East
                standings[game["team"]["name"]] = "E " + str(game["rank"])
            for game in r["response"][0]["league"]["standings"][1]:
                # Stores the name of the team as a key, and the value is it's position in the league, with the "W" of West
                standings[game["team"]["name"]] = "W " + str(game["rank"])

        else:
            # If it's not MLS, just stores the name of the team as a key and it's position as value
            for game in r["response"][0]["league"]["standings"][0]:
                standings[game["team"]["name"]] = game["rank"]

        # Return the standings dict
        return standings
    else:
        return None








