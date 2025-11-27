import argparse
from pathlib import Path
import re
from shutil import copy2, move

from themoviedb import TMDb
from dotenv import load_dotenv
import yaml

load_dotenv()

sample_filenames = [
    "The.Matrix.1999.1080p.BluRay.x264.YIFY.mp4",
    "Inception (2010) [1080p] [BluRay] [YTS.MX].mkv",
    "Avatar-2009-EXTENDED-1080p-BluRay-x264.mp4",
    "Good.Fortune.2025.1080p.WEBRip.x265.10bit.AAC5.1-[YTS.MX].mp4",
    "Dead.Of.Winter.2025.1080p.WEBRip.x264.AAC5.1-[YTS.MX]",
]


YEAR_PATTERN = re.compile(r"(19|20)\d{2}")


def extract_title_and_year(filename: str) -> tuple[str, str | None]:
    """Return a best-effort (title, year) tuple from a release filename."""

    stem = Path(filename).stem
    stem = re.sub(r"[\[\]\(\)\{\}]+", " ", stem)
    normalized = re.sub(r"[._-]+", " ", stem)

    match = YEAR_PATTERN.search(normalized)
    year = match.group(0) if match else None
    title_section = normalized[: match.start()] if match else normalized

    title = re.sub(r"\s+", " ", title_section).strip()
    title = title.title()

    return title, year


def find_movie_files(target_path: Path, extensions: list[str]) -> list[Path]:
    """Return files under target_path that match the configured extensions."""

    normalized_exts = {ext.lower() for ext in extensions}

    if target_path.is_file():
        return [target_path] if target_path.suffix.lower() in normalized_exts else []

    if target_path.is_dir():
        return [
            item
            for item in target_path.rglob("*")
            if item.is_file() and item.suffix.lower() in normalized_exts
        ]

    return []


with open("config.yml", "r") as f:
    config = yaml.safe_load(f)


def find_subtitle_files(movie_file: Path, extensions: list[str]) -> list[Path]:
    """Return subtitle files located near the given movie file."""

    normalized_exts = {ext.lower() for ext in extensions}
    candidate_dirs = [
        movie_file.parent,
        movie_file.parent / "Subs",
        movie_file.parent / "Subtitles",
    ]
    seen: set[Path] = set()
    results: list[Path] = []

    for directory in candidate_dirs:
        if not directory.exists():
            continue
        for ext in normalized_exts:
            for subtitle in directory.glob(f"*{ext}"):
                if subtitle not in seen:
                    seen.add(subtitle)
                    results.append(subtitle)

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Rename movie backups with TMDb")
    parser.add_argument(
        "path",
        nargs="?",
        help="File or directory to scan recursively for movie files",
    )
    args = parser.parse_args()

    tmdb = TMDb()

    filenames_to_process: list[Path] = []
    action = str(config.get("action", "")).lower()
    subtitles_config = config.get("subtitles", {})
    subtitles_enabled = bool(subtitles_config.get("enabled", False))
    subtitle_exts = subtitles_config.get("exts", [])

    if args.path:
        target_path = Path(args.path).expanduser()
        if not target_path.exists():
            raise SystemExit(f"Path not found: {target_path}")

        movie_files = find_movie_files(target_path, config.get("movie_exts", []))
        if movie_files:
            print("Found movie files:")
            for movie_file in movie_files:
                print(f" - {movie_file}")
            filenames_to_process = movie_files
        else:
            print("No movie files found matching configured extensions.")
    else:
        filenames_to_process = [Path(name) for name in sample_filenames]

    for movie_file in filenames_to_process:
        title, year = extract_title_and_year(movie_file.name)
        original_ext = movie_file.suffix
        print(f"Searching for: {title} ({year or 'unknown'})")
        movies = tmdb.search().movies(title, year=year)
        if movies:
            resolved_year = year or (
                movies[0].release_date[:4] if getattr(movies[0], "release_date", None) else "unknown"
            )
            base_filename = config["movie_format"].format(n=movies[0].title, y=resolved_year)
            new_filename = Path(base_filename).with_suffix(original_ext)
            print(f"  Found: {movies[0].title} ({resolved_year})")
            print(f"  new filename: '{new_filename}'")
            subtitle_files: list[Path] = []
            if subtitles_enabled:
                subtitle_files = find_subtitle_files(movie_file, subtitle_exts)
                if subtitle_files:
                    names = ", ".join(sub.name for sub in subtitle_files)
                    print(f"  subtitles found: {names}")
            destination = new_filename
            if action == "copy":
                destination.parent.mkdir(parents=True, exist_ok=True)
                if movie_file.exists():
                    copy2(movie_file, destination)
                    print(f"  copied to: {destination}")
                else:
                    print("  source file not found, skipping copy")
                for subtitle in subtitle_files:
                    sub_destination = destination.with_suffix(subtitle.suffix)
                    if subtitle.exists():
                        copy2(subtitle, sub_destination)
                        print(f"  copied subtitle to: {sub_destination}")
                    else:
                        print(f"  subtitle missing, skipping copy: {subtitle}")
            elif action == "move":
                destination.parent.mkdir(parents=True, exist_ok=True)
                if movie_file.exists():
                    move(movie_file, destination)
                    print(f"  moved to: {destination}")
                else:
                    print("  source file not found, skipping move")
                for subtitle in subtitle_files:
                    sub_destination = destination.with_suffix(subtitle.suffix)
                    if subtitle.exists():
                        move(subtitle, sub_destination)
                        print(f"  moved subtitle to: {sub_destination}")
                    else:
                        print(f"  subtitle missing, skipping move: {subtitle}")
            elif action == "test":
                print(f"  [test] would write: {destination}")
                for subtitle in subtitle_files:
                    sub_destination = destination.with_suffix(subtitle.suffix)
                    print(f"  [test] would write subtitle: {sub_destination}")
        else:
            print("  No results found.")


if __name__ == "__main__":
    main()
