from themoviedb import TMDb
from dotenv import load_dotenv
import yaml

load_dotenv()

with open("config.yml", "r") as f:
    config = yaml.safe_load(f)

print(config)

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
