# SOCCER MASTER

### Description:

Soccer master is a website game where you can try to guess the results of the next games of the Premier League, Brazilian League and MLS (Major League Soccer) soccer leagues.
The project uses the API-FOOTBALL: https://www.api-football.com/
The games available to guess will always start from today's date to tomorrow's date.
The users can guess a maximum number of games, according to their level. First, the users are only able to guess 5 games. The higher the level, the higher the number of games the users can guess.
---
## Cash system
- Simple Guess:
As it sugests, the simple guess is... simple. If the users get the result right, they will win $100.00. On the other hand, if they get wrong, they will lose $30.00.

- Combined Guess:
For the combined guess, the users have to select at least 2 games. To win cash with it, the users have to get all the results right. The amount of cash is what the users normally would win, multiplied by the number of games they guessed. But, if they just get one result wrong, they will lose $30.00 multiplied by the number of games, making the combined guess riskier.
---
## Files
- ### Python Files
    - ##### application.py

        The main file, containing all the flask routs, functions that inserts data to the database, that get all the required information to render all the templates, and others.
        *Note: The functions that make the api calls are not in the application file*
    - ##### helpers.py

        The helpers file has the functions that make the api calls. The file contains:
        - Function for loading apology error messages;
        - The "login_required" function, which ensures that the users are logged in to visit certain pages;
        - Function that makes api call to get all the games that will happen in the correct date, from a provided league
        - "update_games" function, which gets all the user guesses and makes api calls to the games that did not finished, to check if the game is in fact finished and then updating the database if so.
        - Function that updates the users cash, checking the results of their guesses.
        - Function that updates the users level, according to the number of right guesses.
        - The "get_standings" function, that gets the position of the teams in the provided league.

- ### HTML Files
    - ##### Layout:
        The main html file, used for all html files. It contains the links to fonts, jquery, css, etc. In the body there is the navbar of the website, the main jinja block where all of the other files are written, and the footer.
    - ##### Register:
        Simple page where there is a form to the users fill in with their username, password and confirmation, creating an account if everything is correct.
    - ##### Login:
        Simple login page, with a form asking the user's username and password.
    - ##### Index:
        The index file contains the "banner" of the website, where there is an introduction of it. There is also information about the 3 soccer leagues and  some instructions, like the explanation of the features in the website.
    - ##### Games:
        The page  where all the games that can be guessed are displayed. If there is not any games to guess, it will show a message saying that there is not games available.
        Each league has it's own table, with the home team's name, logo and it's position, as well as with the away team, and the datetime of the game. Beside the team's logo and in the middle of the table, there are radio buttons, where users can select to indicate their guesses on that game. The button can be deselected pressing "ctrl".
        In the bottom of the page, there are two buttons, "Simple Guess" and "Combined Guess", which when are pressed, if everything is correct, will indicate the type of the guess in the database.
    - ##### Guesses:
        Page that displays all the guesses from the users. In the top of it, the users can see their right guesses, wrong guesses and their winning porcentage.
        The table which shows all the guesses contains the league name, home team's and away team's name and logo, the datetime of the game, the user guess, the result of the game and the timestamp of the guess.
        After a game is finished, the row color will be green or red, indicating if the user got the result right or wrong, and the exact result of the game will be shown (ex: HomeLogo 1x0 AwayLogo)
    - ##### Delete:
        The delete page displays all the games the user guessed that did not started. The users can select the radio button on the game's row to indicate that they want to delete it, pressing the button in the bottom of the table to do it.
        If the users delete a combined guess which belongs to a group of 2, the guess won't be combined anymore.
    - ##### Tokens:
        Page that displays all the players that can be bought as tokens. It's displayed as a table, informing at each row the name of the player, his team and his price. As with the "games", "guesses" and "delete" pages, there are radio buttons where the users can select to indicate they want to buy a player, pressing the button "buy" at the bottom of the page to do it.
    - ##### Profile:
        As the name sugests, is the profile page of the users. The users can see in it their cash, level, total cash received and total cash spent in tokens, as well as their tokens bought, if any.
    - ##### Users:
        Page that displays the result of a search. If at least one user was found, it will be shown a table with the name of the user. The name of the user(s) found is(are) actually a button, in which if pressed will take to the user's profile.
    - ##### User_Profile:
        This page is pretty much the same to the profile page. The difference is that, in the user profile page, you can see how many guesses the user has made.
    - ##### Apology:
        Page rendered when there is an error message.
    - ##### Password:
        Page that has a form asking the users to provided their current password twice, and then their new password and confirmation.
    - ##### Changed:
        Page rendered after users change their passwords, displaying a confirmation of it.

- ### CSS File
    The css file is very simple. I defined the text font (Arvo) of the whole website on the body tag, made some simple configuration on the main tag and search box, and spend more time in the tokens style, specially in the hover effects.
    I've also got some css from *Bootstrap* (https://getbootstrap.com/) and the search box button from *Font Awesome* (https://fontawesome.com/)

- ### Database File
    - ##### soccermaster.db
        -  ##### users
        - ##### guesses
        - ##### compiled guesses
            Stores the games that already received "cash feedback" (the user already received/lost cash for this guess).
        - ##### fixtures
            Stores the games which can be seen in the "guesses" page. After a game finishes, an api call will be made and this table will be updated.
        - ##### player_tokens
            Stores all the players that can be bought as tokens. The table stores the name, the url for the image, the price and the player's team.
        - ##### user_tokens
            Stores the tokens a user has.

- ### Images Folder:
    You can find in this directory all the player token's images used in the website.
---
## Design
The main thing I tried to achive was a simple design, easier for the users to understand,  with not many things on the screen. But, when it comes to tokens, the page can have a lot of information.
That's why I wanted to make the token's design to look cool, with hover effects and other things.