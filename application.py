import os
import requests

import json

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup_games_by_league, update_games, update_cash, update_level, get_standings


# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///soccermaster.db")


@app.route("/")
def index():
    # Render the index.html
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 400)

        # Ensure username does not exist already
        username = request.form.get("username")
        usernames = db.execute("SELECT username FROM users WHERE username = ?", username)

        # Check if the username already exists
        if len(usernames) != 0:
            return apology("username already exists", 400)

        # Ensure password or confirmation was submitted
        if not request.form.get("password") or not request.form.get("confirmation"):
            return apology("must provide password/confirmation", 400)

        # Ensure password and confirmation are the same
        if request.form.get("password") != request.form.get("confirmation"):
            return apology("passwords do not match", 400)

        # Store the password hash
        hash_password = generate_password_hash(request.form.get("password"), method='pbkdf2:sha256', salt_length=8)

        # Insert the user into the users table
        db.execute("INSERT INTO users (username, hash) VALUES(?, ?)", username, hash_password)

        # Get the user id and remember which user has registered/logged in
        user_id = db.execute("SELECT id FROM users WHERE username = ?", username)
        session["user_id"] = user_id[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/games", methods=["GET"])
@login_required
def games():

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "GET":

        # Get all the games from Brazil, Premier League and MLS
        brazil_games = lookup_games_by_league("71")
        premier_games = lookup_games_by_league("39")
        mls_games = lookup_games_by_league("253")

        # Get the id's of all games that the user has already guessed, and transform in a list.
        user_fixtures_ids = db.execute("SELECT fixture_id FROM guesses WHERE user_id = ?", session["user_id"])
        list_of_ids = [value for elem in user_fixtures_ids for value in elem.values()]

        # Get the user level
        user_level = db.execute("SELECT level FROM users WHERE id = ?", session["user_id"])

        # Get the games that the user guessed and has not finished yet
        guesses_not_finished = db.execute("SELECT COUNT(result) FROM guesses WHERE user_id = ? AND result = ?", session["user_id"], "NF")
        guesses_made = guesses_not_finished[0]["COUNT(result)"]

        # Set the allowed guesses that the users can make, based on their level and number of guesses that he already made
        if user_level[0]["level"] <= 2:
            allowed_guesses = 5
        else:
            allowed_guesses = user_level[0]["level"] + 3

        allowed_guesses -= guesses_made

        # Get the standings from the 3 leagues
        br_standings = get_standings("71")
        pr_standings = get_standings("39")
        mls_standings = get_standings("253")

        # Render the template that will display all the games that the user can guess
        return render_template("games.html", brazil_games=brazil_games, premier_games=premier_games, mls_games=mls_games, list_of_guesses=list_of_ids, allowed_guesses=allowed_guesses, br_standings=br_standings, pr_standings=pr_standings, mls_standings=mls_standings)


@app.route("/guesses", methods=["GET", "POST"])
@login_required
def guesses():

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        number_of_guesses = 0

        # Get the games from Brazil, Premier League and MLS
        brazil_games = lookup_games_by_league("71")
        premier_games = lookup_games_by_league("39")
        mls_games = lookup_games_by_league("253")

        # Set list that will store all the games from the 3 leagues
        games = []

        # Join all games into a single list of games
        if brazil_games:
            games += brazil_games
        if premier_games:
            games += premier_games
        if mls_games:
            games += mls_games

        # Set lists that will store the guess and game info
        guesses = []
        fixtures = []

        for game in games:

            # Get the game button in the "games.html"
            button = request.form.get(str(game["fixture"]["id"]))

            # If the button value is equal to the name of one of the teams or is equal to "Draw", the user has selected this game in the form.
            if button == game["teams"]["home"]["name"] or button == game["teams"]["away"]["name"] or button == "Draw":

                # Update the number of guesses made
                number_of_guesses += 1

                # Check if the guess is combined or simple. The combined feature it's explained in the index page
                if request.form["submit_button"] == "simple":
                    combined = False
                elif request.form["submit_button"] == "combined":
                    combined = True

                # Store in a dict the guess info and append to list
                guess = {
                    # Game ID for API
                    "fixture_id": game["fixture"]["id"],
                    # The name of the team or "Draw"
                    "guess": button,
                    # Boolean that indicates if the guess is combined or not
                    "combined": combined
                }

                guesses.append(guess)

                # To substitute the api, there is a table called fixtures, which stores all the games guessed by all the users. Each game is stored once.
                # So it's necessary to check if the game is already in the database.
                games_compiled = db.execute("SELECT * FROM fixtures WHERE api_id = ?", game["fixture"]["id"])

                # Check if the game is already stored in the database
                if len(games_compiled) == 0:

                    # Get the datetime string
                    datetime = game["fixture"]["date"][:-15] + " " + game["fixture"]["date"][11:-9]

                    # Store in a dict the game info and append to list
                    fixture = {
                        "league": game["league"]["name"],
                        "home_name": game["teams"]["home"]["name"],
                        "home_logo": game["teams"]["home"]["logo"],
                        "away_name" : game["teams"]["away"]["name"],
                        "away_logo": game["teams"]["away"]["logo"],
                        "datetime": datetime,
                        "status": game["fixture"]["status"]["long"],
                        "api_id": game["fixture"]["id"]
                    }

                    fixtures.append(fixture)

        # Check if the user pressed the button to guess, but did not select any games
        if number_of_guesses == 0:
            return apology("You did not guessed any games")
        elif number_of_guesses == 1 and request.form["submit_button"] == "combined":
            return apology("You can't make a combined guess with one game")

        # Insert each of the guesses the user made
        for guess in guesses:
            db.execute("INSERT INTO guesses (user_id, fixture_id, guess, combined) VALUES(?, ?, ?, ?)", session["user_id"], guess["fixture_id"], guess["guess"], guess["combined"])

        # Insert each of the fixtures the user chose
        for fixture in fixtures:
            db.execute("INSERT INTO fixtures (league, home_name, home_logo, away_name, away_logo, datetime, status, api_id) VALUES(?, ?, ?, ?, ?, ?, ?, ?)", fixture["league"], fixture["home_name"], fixture["home_logo"], fixture["away_name"], fixture["away_logo"], fixture["datetime"], fixture["status"], fixture["api_id"])

        # Redirect user to the guesses page
        return redirect("/guesses")

    # User reached route via GET (as by clicking a link or via redirect)
    else:

        # The function update_games returns all the games guessed by the user,
        # but also checks if a game in the database is stored as "Not Finished" and the game is in fact finished, updating the database.
        guessed_games = update_games()

        # Get all the info from the user to show his history of guesses
        user_info = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])

        # Render the template that will show all the user guesses
        return render_template("guesses.html", guessed_games=guessed_games, user=user_info[0])


@app.route("/tokens")
@login_required
def tokens():

    # Get all the players that can be bought as tokens and the number of tokens the user has
    players = db.execute("SELECT * FROM player_tokens ORDER BY price DESC")
    number_of_user_tokens = db.execute("SELECT COUNT(token_id) FROM user_tokens WHERE user_id = ?", session["user_id"])

    # Check if the user bought all the tokens or not, and set the variable "tokens_left"
    if number_of_user_tokens[0]["COUNT(token_id)"] == len(players):
        tokens_left = False
    else:
        tokens_left = True

    # Get a list with all the id's of the tokens owned by the user. This will be used to not display the players that the user already bought
    user_tokens = db.execute("SELECT id FROM user_tokens WHERE user_id = ?", session["user_id"])
    list_of_tokens = [value for elem in user_tokens for value in elem.values()]

    # Get the user's current cash
    cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])

    # Render the template that will display all the players that can be bought as tokens
    return render_template("tokens.html", players=players, user_tokens=list_of_tokens, tokens_left=tokens_left, cash=cash[0]["cash"])


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():

    # User reached route via POST (submitting a form via POST, for buying a player token)
    if request.method == "POST":

        # Get the current cash from the user
        cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])
        # Get all the players that can be bought as tokens
        players = db.execute("SELECT * FROM player_tokens")

        # Set the necessary variables
        total_price = 0
        number_of_tokens = 0
        tokens_bought = []

        # Go through each player
        for player in players:
            # Get the button from the player row (in tokens.html)
            button_value = request.form.get(str(player["id"]))

            # If the button value corresponds to the name of a player, the user has bought this token (selected this button)
            if button_value == player["name"]:

                # Insert the token's id into the tokens bought list
                tokens_bought.append(player["id"])

                # Updates the total price that the user will pay (or not) and the number of tokens bought
                total_price += player["price"]
                number_of_tokens += 1

        # Check if the user pressed the button "buy" but did not select any players
        if number_of_tokens == 0:
            return apology("you did not select any token")

        # Check if the user can afford the purchase
        if cash[0]["cash"] < total_price:
            return apology("You need more cash, sorry")
        else:
            # Go through each token in the tokens list and insert into the database
            for token in tokens_bought:
                db.execute("INSERT INTO user_tokens (user_id, token_id) VALUES(?, ?)", session["user_id"], token)
            # Update the user cash
            db.execute("UPDATE users SET cash = ? WHERE id = ?", cash[0]["cash"] - total_price, session["user_id"])

        # Redirect user to the profile page
        return redirect("/profile")

    # User reached route via GET (as by clicking a link or via redirect)
    else:

        update_cash()
        update_level()

        # Get all the user info
        user_info = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])
        user_tokens = db.execute("SELECT * FROM player_tokens WHERE id IN (SELECT token_id FROM user_tokens WHERE user_id = ?)", session["user_id"])

        # Set the variable spent which will show how much the user has spent with tokens
        spent = 0

        # Go through each token and add the price of it in the variable
        for token in user_tokens:
            spent += token["price"]

        # Render the profile page which will display all the info
        return render_template("profile.html", user=user_info[0], user_tokens=user_tokens, number_of_tokens=len(user_tokens), spent=spent)


@app.route("/users", methods=["POST"])
@login_required
def users():

    # This page will be shown when the user type in the search box to find other users.

    # Get the user input
    string = request.form.get("search")

    # Check if the user has type something, and if so, search in the database
    if string:
        users = db.execute("SELECT * FROM users WHERE username LIKE ? AND NOT id = ?", (f'%{string}%',), session["user_id"])
    else:
        users = []

    # Render the users page which will display the result of the search
    return render_template("users.html", users=users)


@app.route("/user_profile", methods=["POST"])
@login_required
def user_profile():

    # Get the username and the user info/tokens from the "users" page
    user = request.form.get("user")
    user_info = db.execute("SELECT * FROM users WHERE username = ?", user)
    user_tokens = db.execute("SELECT * FROM player_tokens WHERE id IN (SELECT token_id FROM user_tokens WHERE user_id = ?)", user_info[0]["id"])
    number_of_guesses = db.execute("SELECT COUNT(id) FROM guesses WHERE user_id = ?", user_info[0]["id"])

    # Get what the user has spent with tokens
    spent = 0
    for token in user_tokens:
        spent += token["price"]

    # Render the profile from another user
    return render_template("user_profile.html", user=user_info[0], user_tokens=user_tokens, number_of_guesses=number_of_guesses[0]["COUNT(id)"], number_of_tokens=len(user_tokens), spent=spent)


@app.route("/password", methods=["GET", "POST"])
@login_required
def change_password():
    """Change user password"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure passwords were submitted
        if not request.form.get("password") or not request.form.get("confirmation") or not request.form.get("newpass") or not request.form.get("newconf"):
            return apology("must provide password/new password and/or confirmation password", 403)

        # Check if the current password and the password confirmation match
        if request.form.get("password") != request.form.get("confirmation"):
            return apology("current password and confirmation do not match", 403)

        # Store the hash of the current password
        user_hash = db.execute("SELECT hash FROM users WHERE id = ?", session["user_id"])

        # Check if the current password match with the current password provided by the user
        if not check_password_hash(user_hash[0]["hash"], request.form.get("password")):
            return apology("invalid password", 403)

        # Check if the new password match with the new password confirmation
        if request.form.get("newpass") != request.form.get("newconf"):
            return apology("new password and confirmation do not match", 403)

        # Check if the new password is equal to the old password
        if request.form.get("newpass") == request.form.get("password"):
            return apology("new password provided is your current password", 400)

        # Store the new password hash
        hash_password = generate_password_hash(request.form.get("newpass"), method='pbkdf2:sha256', salt_length=8)
        # Update the password in the users table
        db.execute("UPDATE users SET hash = ? WHERE id = ?", hash_password, session["user_id"])

        # Return to the "changed" page, where will be displayed to the user that the password was changed
        return render_template("changed.html")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("password.html")


@app.route("/delete", methods=["POST", "GET"])
@login_required
def delete():

    # Page that you can delete guesses, as long as the game has not started

    # Get the user guesses and updates it
    guessed_games = update_games()

    # Set list that will store the games that can be deleted
    not_started_games = []

    # Go through each guess of the user and check if the game has not started, appending to the list if so
    for guess in guessed_games:
        if guess["status"] == "Not Started":
            not_started_games.append(guess)

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        number_of_sales = 0

        # Go through each game not started
        for guess in not_started_games:

            # Get the button from the table in "delete.html"
            button = request.form.get(str(guess["id"]))

            # If the value of the button is the fixture API ID, the user wants to delete this game (selected the button)
            if button == str(guess["api_id"]):

                number_of_sales += 1

                # Checks if the guess is combined
                if guess["combined"]:
                    # Gets the combined group which the guess belongs
                    group = db.execute("SELECT * FROM guesses WHERE combined = ? AND timestamp = ? AND user_id = ?", True, guess["timestamp"], session["user_id"])
                    # If the group is composed by two games, not only the guess will be delete, as well the other game will not longer be combined.
                    if len(group) == 2:
                        db.execute("UPDATE guesses SET combined = ? WHERE timestamp = ? AND user_id = ?", False, guess["timestamp"], session["user_id"])

                # Delete the guess from the database
                db.execute("DELETE FROM guesses WHERE user_id = ? AND fixture_id = ?", session["user_id"], guess["api_id"])

        # Check if the user did not select any games
        if number_of_sales == 0:
            return apology("you did not delete any guesses")

        # Redirect user to the guesses page
        return redirect("/guesses")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        # Render the delete page
        return render_template("delete.html", not_started_games=not_started_games)

