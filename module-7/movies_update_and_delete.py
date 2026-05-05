"""
    Author: Zachary White
    Instructor: Sue Sampson
    Date: 05/01/2026
    Assignment: Module 7 - Movies Update & Delete
    Description: Python script to insert, update, and delete records
                 in the movies MySQL database
"""

""" import statements """
import mysql.connector  # to connect
from mysql.connector import errorcode

import dotenv  # to use .env file
from dotenv import dotenv_values

# load .env file
secrets = dotenv_values(".env")

# database config
config = {
    "user": secrets["USER"],
    "password": secrets["PASSWORD"],
    "host": secrets["HOST"],
    "database": secrets["DATABASE"],
    "raise_on_warnings": True
}

# -------------------------------------------
# -- Function to display film records
# -- Defined OUTSIDE try block
# -------------------------------------------
def show_films(cursor, title):
    cursor.execute(
        "SELECT film_name as Name, film_director as Director, "
        "genre_name as Genre, studio_name as 'Studio Name' "
        "FROM film "
        "INNER JOIN genre ON film.genre_id = genre.genre_id "
        "INNER JOIN studio ON film.studio_id = studio.studio_id"
    )
    films = cursor.fetchall()

    print("\n  -- {} --".format(title))

    for film in films:
        print("Film Name: {}".format(film[0]))
        print("Director: {}".format(film[1]))
        print("Genre Name ID: {}".format(film[2]))
        print("Studio Name: {}\n".format(film[3]))


# -------------------------------------------
# -- Main program
# -------------------------------------------
try:
    db = mysql.connector.connect(**config)

    print("\nDatabase user {} connected to MySQL on host {} with database {}".format(
        config["user"], config["host"], config["database"]
    ))

    input("\nPress any key to continue...")

    cursor = db.cursor()

    # Display films before any changes
    show_films(cursor, "DISPLAYING FILMS")

    # Insert The Matrix
    cursor.execute(
        "INSERT INTO film (film_name, film_director, genre_id, studio_id, film_runtime, film_releaseDate) "
        "VALUES ('The Matrix', 'Lana Wachowski', 2, 1, 136, '1999')"
    )
    db.commit()

    # Display films after insert
    show_films(cursor, "DISPLAYING FILMS AFTER INSERT")

    # Update Alien to Horror genre (genre_id = 1)
    cursor.execute(
        "UPDATE film SET genre_id = 1 WHERE film_name = 'Alien'"
    )
    db.commit()

    # Display films after update
    show_films(cursor, "DISPLAYING FILMS AFTER UPDATE - Changed Alien to Horror")

    # Delete Gladiator from the film table
    cursor.execute(
        "DELETE FROM film WHERE film_name = 'Gladiator'"
    )
    db.commit()

    # Display films after delete
    show_films(cursor, "DISPLAYING FILMS AFTER DELETE - Gladiator Removed")

except mysql.connector.Error as err:
    if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
        print("  The supplied username or password are invalid")
    elif err.errno == errorcode.ER_BAD_DB_ERROR:
        print("  The specified database does not exist")
    else:
        print(err)

finally:
    db.close()