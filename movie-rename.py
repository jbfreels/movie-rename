from themoviedb import TMDb
from dotenv import load_dotenv

load_dotenv()


if __name__ == "__main__":
    tmdb = TMDb()
    movies = tmdb.search().movies("fight", year="1999")

    if movies:
        movie = movies[0]
        print(movie.title)
        print(movie.overview)
        print(movie.release_date)
    else:
        print("no movie found")
