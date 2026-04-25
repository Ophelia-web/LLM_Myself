import argparse
import asyncio
import json
import logging
import os

from app.services.image_analyzer import analyze_restaurant_images


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run isolated VLM analysis for one image URL."
    )
    parser.add_argument("--gemini-key", required=True, help="Gemini API key")
    parser.add_argument(
        "--image-url",
        required=True,
        help="Single restaurant image URL (Google Place Photo URL works).",
    )
    parser.add_argument(
        "--name",
        default="Test Restaurant",
        help="Restaurant name label for prompt context.",
    )
    parser.add_argument(
        "--cuisine",
        default="unknown",
        help="Cuisine label for prompt context.",
    )
    return parser.parse_args()


async def run_test(args: argparse.Namespace) -> None:
    os.environ["GEMINI_API_KEY"] = args.gemini_key
    result = await analyze_restaurant_images(
        restaurant_name=args.name,
        cuisine=args.cuisine,
        photo_urls=[args.image_url],
    )
    print(json.dumps(result.model_dump(), indent=2, ensure_ascii=True))


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    args = parse_args()
    asyncio.run(run_test(args))


if __name__ == "__main__":
    main()
